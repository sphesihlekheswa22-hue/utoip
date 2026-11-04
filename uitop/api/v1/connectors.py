"""Site connectors API — LAN scanners for cloud UITOP."""
from flask import Blueprint, g, request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import agent_scope_required, permission_required
from uitop.core.permissions import (
    AGENTS_MANAGE,
    CONNECTORS_HEARTBEAT,
    CONNECTORS_MANAGE,
    CONNECTORS_NETWORK_INGEST,
    CONNECTORS_PRINTER_INGEST,
)
from uitop.schemas import created, success
from uitop.services import agents as agents_service
from uitop.services import site_connectors as conn_svc

bp = Blueprint("connectors", __name__, url_prefix="/connectors")


@bp.get("/health")
def health():
    return success({"status": "ok", "service": "connectors"})


@bp.post("/enrollment-tokens")
@permission_required(AGENTS_MANAGE)
def create_enrollment_token():
    """Create an enrollment token intended for site connectors (same token table as agents)."""
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    token, raw = agents_service.create_enrollment_token(
        label=payload.get("label") or "Site connector enrollment",
        created_by_id=actor_id,
        expires_hours=payload.get("expires_hours", 168),
        max_uses=payload.get("max_uses", 10),
    )
    data = token.to_dict()
    data["token"] = raw
    data["purpose"] = "site_connector"
    return created(data)


@bp.get("/")
@permission_required(CONNECTORS_MANAGE)
def list_sites():
    rows = conn_svc.list_connectors()
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})


@bp.post("/register")
def register():
    """Public — enroll a site connector with an enrollment token (does not create a Computer)."""
    payload = request.get_json(silent=True) or {}
    result = conn_svc.register_connector(
        enrollment_token=payload.get("enrollment_token"),
        site_name=payload.get("site_name") or payload.get("name"),
        hostname=payload.get("hostname"),
        connector_version=payload.get("connector_version") or payload.get("agent_version"),
        cidrs=payload.get("cidrs"),
    )
    return created(result)


@bp.post("/token")
def token():
    """Exchange connector client credentials for a JWT (same as agents)."""
    payload = request.get_json(silent=True) or {}
    result = agents_service.exchange_client_credentials(
        client_id=payload.get("client_id"),
        client_secret=payload.get("client_secret"),
    )
    return success(result)


@bp.post("/heartbeat")
@agent_scope_required(CONNECTORS_HEARTBEAT)
def heartbeat():
    payload = request.get_json(silent=True) or {}
    return success(conn_svc.heartbeat(g.agent_client, payload))


@bp.post("/network-scan")
@agent_scope_required(CONNECTORS_NETWORK_INGEST)
def network_scan():
    payload = request.get_json(silent=True) or {}
    return success(conn_svc.ingest_network_scan(g.agent_client, payload))


@bp.post("/printers")
@agent_scope_required(CONNECTORS_PRINTER_INGEST)
def printers():
    payload = request.get_json(silent=True) or {}
    return success(conn_svc.ingest_printers(g.agent_client, payload))
