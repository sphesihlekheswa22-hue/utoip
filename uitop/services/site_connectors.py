"""Site connector registration, heartbeat, and discovery ingest."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from uitop.core.errors import NotFoundError, UnauthorizedError, ValidationError
from uitop.core.permissions import DEFAULT_CONNECTOR_SCOPES
from uitop.core.security import hash_secret, verify_secret
from uitop.extensions import db
from uitop.models.api_client import ApiClient
from uitop.models.auth import AgentEnrollmentToken
from uitop.models.site_connector import SiteConnector
from uitop.services.audit import log_audit
from uitop.services import network_scan as scan_svc


def utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _match_enrollment(enrollment_token: str) -> AgentEnrollmentToken:
    if not enrollment_token:
        raise ValidationError("enrollment_token is required")
    prefix = enrollment_token[:12]
    candidates = AgentEnrollmentToken.query.filter_by(token_prefix=prefix).all()
    for candidate in candidates:
        if verify_secret(candidate.token_hash, enrollment_token) and candidate.is_active:
            return candidate
    raise UnauthorizedError("Invalid or expired enrollment token")


def register_connector(
    *,
    enrollment_token: str,
    site_name: str | None = None,
    hostname: str | None = None,
    connector_version: str | None = None,
    cidrs: list[str] | None = None,
) -> dict:
    matched = _match_enrollment(enrollment_token)

    client_id = f"conn_{uuid.uuid4().hex[:16]}"
    client_secret = secrets.token_urlsafe(32)
    connector_id = f"connector-{uuid.uuid4().hex[:12]}"
    host = (hostname or "").strip() or f"site-{connector_id[-8:]}"
    name = (site_name or "").strip() or host

    client = ApiClient(
        client_id=client_id,
        name=f"Site connector · {name}"[:120],
        secret_hash=hash_secret(client_secret),
        scopes=list(DEFAULT_CONNECTOR_SCOPES),
        agent_id=connector_id,
        hostname=host,
    )
    matched.use_count += 1
    db.session.add(client)
    db.session.flush()

    site = SiteConnector(
        site_name=name[:120],
        connector_id=connector_id,
        api_client_id=client.id,
        hostname=host[:255],
        connector_version=(connector_version or "")[:40] or None,
        status="registered",
        cidrs_json=list(cidrs or []),
        last_seen_at=utcnow(),
        is_active=True,
    )
    db.session.add(site)
    db.session.commit()

    log_audit(
        "connectors.register",
        actor_client_id=client_id,
        resource_type="site_connector",
        resource_id=site.id,
        meta={"connector_id": connector_id, "site_name": name},
    )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "connector_id": connector_id,
        "site_id": site.id,
        "site_name": site.site_name,
        "scopes": client.scopes,
    }


def _site_for_client(client: ApiClient) -> SiteConnector:
    site = SiteConnector.query.filter_by(connector_id=client.agent_id, is_active=True).first()
    if site is None and client.id:
        site = SiteConnector.query.filter_by(api_client_id=client.id, is_active=True).first()
    if site is None:
        raise NotFoundError("Site connector not registered for this client")
    return site


def heartbeat(client: ApiClient, payload: dict) -> dict:
    site = _site_for_client(client)
    now = utcnow()
    site.last_seen_at = now
    site.status = (payload.get("status") or "online").strip().lower() or "online"
    if payload.get("hostname"):
        site.hostname = str(payload["hostname"])[:255]
        client.hostname = site.hostname
    if payload.get("ip_address"):
        site.ip_address = str(payload["ip_address"])[:64]
    if payload.get("connector_version"):
        site.connector_version = str(payload["connector_version"])[:40]
    if payload.get("cidrs"):
        site.cidrs_json = list(payload["cidrs"])
    if payload.get("last_scan_at"):
        site.last_scan_at = _parse_dt(payload["last_scan_at"]) or site.last_scan_at
    if payload.get("stats"):
        site.last_stats_json = payload["stats"]
    client.last_used_at = now
    db.session.commit()
    return {
        "site_id": site.id,
        "connector_id": site.connector_id,
        "status": site.status,
        "last_seen_at": site.last_seen_at.isoformat() if site.last_seen_at else None,
        "server_time": now.isoformat(),
    }


def ingest_network_scan(client: ApiClient, payload: dict) -> dict:
    site = _site_for_client(client)
    hosts = payload.get("hosts") or []
    if not isinstance(hosts, list):
        raise ValidationError("hosts must be a list")
    prefer = payload.get("prefer_type")
    result = scan_svc.upsert_discovered_hosts(hosts, prefer_type=prefer, site_id=site.id)
    site.last_scan_at = _parse_dt(payload.get("scanned_at")) or utcnow()
    site.last_seen_at = utcnow()
    site.status = "online"
    site.last_stats_json = {
        "cidr": payload.get("cidr"),
        "hosts": len(hosts),
        "created": result.get("created_count", 0),
        "updated": result.get("updated_count", 0),
    }
    if payload.get("cidr"):
        cidrs = list(site.cidrs_json or [])
        if payload["cidr"] not in cidrs:
            cidrs.append(payload["cidr"])
            site.cidrs_json = cidrs[:20]
    client.last_used_at = utcnow()
    db.session.commit()
    log_audit(
        "connectors.network_ingest",
        actor_client_id=client.client_id,
        resource_type="site_connector",
        resource_id=site.id,
        meta={"cidr": payload.get("cidr"), **{k: result.get(k) for k in ("created_count", "updated_count")}},
    )
    return result


def ingest_printers(client: ApiClient, payload: dict) -> dict:
    site = _site_for_client(client)
    printers = payload.get("printers") or []
    if not isinstance(printers, list):
        raise ValidationError("printers must be a list")
    result = scan_svc.apply_printer_telemetry(printers, site_id=site.id)
    site.last_seen_at = utcnow()
    site.status = "online"
    client.last_used_at = utcnow()
    db.session.commit()
    log_audit(
        "connectors.printer_ingest",
        actor_client_id=client.client_id,
        resource_type="site_connector",
        resource_id=site.id,
        meta={"count": len(printers), "created": result.get("created_count"), "updated": result.get("updated_count")},
    )
    return result


def list_connectors() -> list[SiteConnector]:
    return SiteConnector.query.order_by(SiteConnector.updated_at.desc()).all()


def get_connector(site_id: int) -> SiteConnector:
    site = db.session.get(SiteConnector, site_id)
    if not site:
        raise NotFoundError("Site connector not found")
    return site
