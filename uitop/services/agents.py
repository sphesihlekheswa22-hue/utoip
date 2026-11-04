"""Agent enrollment, credentials, and telemetry ingestion."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from flask_jwt_extended import create_access_token

from uitop.core.errors import ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from uitop.core.permissions import DEFAULT_AGENT_SCOPES
from uitop.core.security import hash_secret, verify_secret
from uitop.extensions import db
from uitop.models.agent_telemetry import AgentAlert, AgentEvent, PerformanceSample
from uitop.models.api_client import ApiClient
from uitop.models.auth import AgentEnrollmentToken
from uitop.models.inventory import Computer
from uitop.services.audit import log_audit


def utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(value, *, field: str = "timestamp", default: datetime | None = None) -> datetime | None:
    if value is None or value == "":
        return default
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except (ValueError, TypeError) as exc:
            raise ValidationError(f"Invalid {field}", details={field: value}) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_enrollment_token(
    *,
    label: str,
    created_by_id: int | None,
    expires_hours: int | None = 168,
    max_uses: int | None = 50,
) -> tuple[AgentEnrollmentToken, str]:
    raw = f"enroll_{secrets.token_urlsafe(24)}"
    token = AgentEnrollmentToken(
        label=label,
        token_hash=hash_secret(raw),
        token_prefix=raw[:12],
        expires_at=utcnow() + timedelta(hours=expires_hours) if expires_hours else None,
        max_uses=max_uses,
        created_by_id=created_by_id,
    )
    db.session.add(token)
    db.session.commit()
    log_audit(
        "agents.enrollment_created",
        actor_user_id=created_by_id,
        resource_type="agent_enrollment_token",
        resource_id=token.id,
        meta={"label": label},
    )
    return token, raw


def register_agent(
    enrollment_token: str,
    hostname: str | None = None,
    name: str | None = None,
    agent_version: str | None = None,
) -> dict:
    if not enrollment_token:
        raise ValidationError("enrollment_token is required")

    prefix = enrollment_token[:12]
    candidates = AgentEnrollmentToken.query.filter_by(token_prefix=prefix).all()
    matched = None
    for candidate in candidates:
        if verify_secret(candidate.token_hash, enrollment_token) and candidate.is_active:
            matched = candidate
            break
    if matched is None:
        raise UnauthorizedError("Invalid or expired enrollment token")

    client_id = f"agt_{uuid.uuid4().hex[:16]}"
    client_secret = secrets.token_urlsafe(32)
    agent_id = f"agent-{uuid.uuid4().hex[:12]}"
    host = (hostname or "").strip() or f"host-{agent_id[-8:]}"

    client = ApiClient(
        client_id=client_id,
        name=name or host,
        secret_hash=hash_secret(client_secret),
        scopes=list(DEFAULT_AGENT_SCOPES),
        agent_id=agent_id,
        hostname=host,
    )
    matched.use_count += 1
    db.session.add(client)

    computer = Computer(
        hostname=host,
        agent_id=agent_id,
        agent_version=agent_version,
        status="registered",
        last_seen_at=utcnow(),
    )
    db.session.add(computer)
    db.session.commit()

    log_audit(
        "agents.register",
        actor_client_id=client_id,
        resource_type="api_client",
        resource_id=client.id,
        meta={"agent_id": agent_id, "hostname": host, "computer_id": computer.id},
    )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "agent_id": agent_id,
        "scopes": client.scopes,
        "computer_id": computer.id,
    }


def exchange_client_credentials(client_id: str, client_secret: str) -> dict:
    if not client_id or not client_secret:
        raise ValidationError("client_id and client_secret are required")
    client = ApiClient.query.filter_by(client_id=client_id).first()
    if client is None or not client.is_active:
        raise UnauthorizedError("Invalid client credentials")
    if not verify_secret(client.secret_hash, client_secret):
        raise UnauthorizedError("Invalid client credentials")

    client.last_used_at = utcnow()
    db.session.commit()

    expires = timedelta(hours=1)
    access_token = create_access_token(
        identity=client.client_id,
        additional_claims={
            "token_use": "agent",
            "agent_id": client.agent_id,
            "scopes": client.scopes or [],
            "hostname": client.hostname,
        },
        expires_delta=expires,
    )

    log_audit(
        "agents.token",
        actor_client_id=client_id,
        resource_type="api_client",
        resource_id=client.id,
        meta={"agent_id": client.agent_id},
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(expires.total_seconds()),
        "agent_id": client.agent_id,
        "scopes": client.scopes or [],
    }


def get_enrollment_or_404(token_id: int) -> AgentEnrollmentToken:
    token = AgentEnrollmentToken.query.get(token_id)
    if token is None:
        raise NotFoundError("Enrollment token not found")
    return token


def revoke_enrollment(token_id: int, actor_user_id: int | None = None) -> AgentEnrollmentToken:
    token = get_enrollment_or_404(token_id)
    if token.revoked_at:
        raise ForbiddenError("Token already revoked")
    token.revoked_at = utcnow()
    db.session.commit()
    log_audit(
        "agents.enrollment_revoked",
        actor_user_id=actor_user_id,
        resource_type="agent_enrollment_token",
        resource_id=token.id,
    )
    return token


def _computer_for_agent(client: ApiClient) -> Computer | None:
    if not client.agent_id:
        return None
    return Computer.query.filter_by(agent_id=client.agent_id).first()


def heartbeat(client: ApiClient, payload: dict) -> dict:
    now = utcnow()
    status = (payload.get("status") or "online").strip().lower()
    agent_version = payload.get("agent_version") or payload.get("version")
    hostname = payload.get("hostname")
    ip_address = payload.get("ip_address")

    client.last_used_at = now
    if hostname:
        client.hostname = hostname

    computer = _computer_for_agent(client)
    if computer is None:
        computer = Computer(
            hostname=hostname or client.hostname or f"host-{client.agent_id[-8:]}",
            agent_id=client.agent_id,
            status=status,
            agent_version=agent_version,
            last_seen_at=now,
            ip_address=ip_address,
        )
        db.session.add(computer)
    else:
        computer.last_seen_at = now
        computer.status = status
        if agent_version:
            computer.agent_version = agent_version
        if hostname:
            computer.hostname = hostname
        if ip_address:
            computer.ip_address = ip_address

    db.session.commit()
    log_audit(
        "agents.heartbeat",
        actor_client_id=client.client_id,
        resource_type="computer",
        resource_id=computer.id,
        meta={"agent_id": client.agent_id, "status": status, "agent_version": agent_version},
    )
    return {
        "agent_id": client.agent_id,
        "computer_id": computer.id,
        "status": computer.status,
        "agent_version": computer.agent_version,
        "last_seen_at": computer.last_seen_at.isoformat() if computer.last_seen_at else None,
        "server_time": now.isoformat(),
    }


_INVENTORY_FIELDS = (
    "hostname",
    "asset_tag",
    "ip_address",
    "mac_address",
    "os_name",
    "os_version",
    "manufacturer",
    "model",
    "serial_number",
    "domain",
    "cpu_model",
    "cpu_cores",
    "ram_gb",
    "disk_gb",
)


def upsert_inventory(client: ApiClient, payload: dict) -> dict:
    inventory = payload.get("inventory") if isinstance(payload.get("inventory"), dict) else payload
    if not isinstance(inventory, dict) or not inventory:
        raise ValidationError("inventory payload is required")

    now = utcnow()
    computer = _computer_for_agent(client)
    hostname = inventory.get("hostname") or client.hostname or f"host-{client.agent_id[-8:]}"

    if computer is None:
        computer = Computer(hostname=hostname, agent_id=client.agent_id, status="online")
        db.session.add(computer)

    for field in _INVENTORY_FIELDS:
        if field in inventory and inventory[field] is not None:
            setattr(computer, field, inventory[field])

    if not computer.hostname:
        computer.hostname = hostname

    agent_version = payload.get("agent_version") or inventory.get("agent_version")
    if agent_version:
        computer.agent_version = agent_version

    computer.inventory_payload = inventory
    computer.inventory_updated_at = now
    computer.last_seen_at = now
    if computer.status in {None, "unknown", "registered"}:
        computer.status = "online"

    client.last_used_at = now
    if inventory.get("hostname"):
        client.hostname = inventory["hostname"]

    db.session.flush()
    from uitop.services.assets import ensure_asset_for_computer

    ensure_asset_for_computer(computer, actor_client_id=client.client_id)
    db.session.commit()

    # Link to UITOP user when agent reports Windows login
    try:
        from uitop.services.device_detection import (
            _normalize_login,
            ensure_user_owns_computer,
            inventory_login,
            user_login_aliases,
        )
        from uitop.models.user import User

        login = inventory_login(computer) or _normalize_login(
            str((inventory or {}).get("logged_in_user") or (inventory or {}).get("windows_user") or "")
        )
        if login:
            for user in User.query.filter_by(is_active=True).all():
                if login in user_login_aliases(user):
                    ensure_user_owns_computer(user, computer, source="agent login")
                    db.session.commit()
                    break
    except Exception:
        pass

    log_audit(
        "agents.inventory",
        actor_client_id=client.client_id,
        resource_type="computer",
        resource_id=computer.id,
        meta={"agent_id": client.agent_id, "hostname": computer.hostname},
    )
    return {"computer": computer.to_dict(), "updated": True}


def ingest_performance(client: ApiClient, payload: dict) -> dict:
    samples_in = payload.get("samples")
    if samples_in is None:
        samples_in = [payload]
    if not isinstance(samples_in, list) or not samples_in:
        raise ValidationError("samples list is required")

    computer = _computer_for_agent(client)
    created = []
    now = utcnow()

    for item in samples_in:
        if not isinstance(item, dict):
            raise ValidationError("Each sample must be an object")
        sample = PerformanceSample(
            agent_id=client.agent_id,
            computer_id=computer.id if computer else None,
            collected_at=_parse_dt(item.get("collected_at") or item.get("timestamp"), field="collected_at")
            or utcnow(),
            cpu_percent=item.get("cpu_percent"),
            memory_percent=item.get("memory_percent"),
            memory_used_mb=item.get("memory_used_mb"),
            memory_total_mb=item.get("memory_total_mb"),
            disk_percent=item.get("disk_percent"),
            disk_used_gb=item.get("disk_used_gb"),
            disk_total_gb=item.get("disk_total_gb"),
            network_bytes_sent=item.get("network_bytes_sent"),
            network_bytes_recv=item.get("network_bytes_recv"),
            process_count=item.get("process_count"),
            uptime_seconds=item.get("uptime_seconds"),
            meta=item.get("meta"),
        )
        db.session.add(sample)
        created.append(sample)

    if computer:
        computer.last_seen_at = now
        computer.status = payload.get("status") or computer.status or "online"
    client.last_used_at = now
    db.session.commit()

    log_audit(
        "agents.performance",
        actor_client_id=client.client_id,
        resource_type="computer",
        resource_id=computer.id if computer else None,
        meta={"agent_id": client.agent_id, "count": len(created)},
    )
    return {"accepted": len(created), "samples": [s.to_dict() for s in created]}


def ingest_events(client: ApiClient, payload: dict) -> dict:
    events_in = payload.get("events")
    if events_in is None:
        events_in = [payload]
    if not isinstance(events_in, list) or not events_in:
        raise ValidationError("events list is required")

    computer = _computer_for_agent(client)
    created = []
    now = utcnow()

    for item in events_in:
        if not isinstance(item, dict):
            raise ValidationError("Each event must be an object")
        message = item.get("message")
        event_type = item.get("event_type") or item.get("type")
        if not message or not event_type:
            raise ValidationError("event_type and message are required for each event")
        event = AgentEvent(
            agent_id=client.agent_id,
            computer_id=computer.id if computer else None,
            event_type=str(event_type)[:64],
            severity=(item.get("severity") or "info")[:32],
            message=str(message)[:512],
            source=(item.get("source") or None),
            occurred_at=_parse_dt(item.get("occurred_at") or item.get("timestamp"), field="occurred_at")
            or utcnow(),
            meta=item.get("meta"),
        )
        db.session.add(event)
        created.append(event)

    if computer:
        computer.last_seen_at = now
    client.last_used_at = now
    db.session.commit()

    log_audit(
        "agents.events",
        actor_client_id=client.client_id,
        resource_type="computer",
        resource_id=computer.id if computer else None,
        meta={"agent_id": client.agent_id, "count": len(created)},
    )
    return {"accepted": len(created), "events": [e.to_dict() for e in created]}


def ingest_alerts(client: ApiClient, payload: dict) -> dict:
    alerts_in = payload.get("alerts")
    if alerts_in is None:
        alerts_in = [payload]
    if not isinstance(alerts_in, list) or not alerts_in:
        raise ValidationError("alerts list is required")

    computer = _computer_for_agent(client)
    created = []
    now = utcnow()

    for item in alerts_in:
        if not isinstance(item, dict):
            raise ValidationError("Each alert must be an object")
        title = item.get("title")
        alert_code = item.get("alert_code") or item.get("code")
        if not title or not alert_code:
            raise ValidationError("alert_code and title are required for each alert")
        status = (item.get("status") or "open").lower()
        occurred_at = _parse_dt(item.get("occurred_at") or item.get("timestamp"), field="occurred_at") or now
        resolved_at = _parse_dt(item.get("resolved_at"), field="resolved_at", default=None)
        if status == "resolved" and resolved_at is None:
            resolved_at = now
        alert = AgentAlert(
            agent_id=client.agent_id,
            computer_id=computer.id if computer else None,
            alert_code=str(alert_code)[:64],
            severity=(item.get("severity") or "warning")[:32],
            title=str(title)[:255],
            message=(str(item["message"])[:1024] if item.get("message") else None),
            status=status[:32],
            occurred_at=occurred_at,
            resolved_at=resolved_at,
            meta=item.get("meta"),
        )
        db.session.add(alert)
        created.append(alert)

    if computer:
        computer.last_seen_at = now
    client.last_used_at = now
    db.session.commit()

    log_audit(
        "agents.alerts",
        actor_client_id=client.client_id,
        resource_type="computer",
        resource_id=computer.id if computer else None,
        meta={"agent_id": client.agent_id, "count": len(created)},
    )
    return {"accepted": len(created), "alerts": [a.to_dict() for a in created]}
