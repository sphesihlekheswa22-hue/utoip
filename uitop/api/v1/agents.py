"""Agents API — enrollment, credentials, and telemetry ingestion."""
from flask import Blueprint, g, request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import agent_scope_required, permission_required
from uitop.core.permissions import (
    AGENTS_ALERTS,
    AGENTS_EVENTS,
    AGENTS_HEARTBEAT,
    AGENTS_INVENTORY,
    AGENTS_MANAGE,
    AGENTS_PERFORMANCE,
)
from uitop.models.auth import AgentEnrollmentToken
from uitop.schemas import created, success
from uitop.services import agents as agents_service

bp = Blueprint("agents", __name__, url_prefix="/agents")


@bp.get("/health")
def health():
    return success({"status": "ok", "service": "agents"})


@bp.post("/enrollment-tokens")
@permission_required(AGENTS_MANAGE)
def create_enrollment_token():
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    token, raw = agents_service.create_enrollment_token(
        label=payload.get("label") or "Default enrollment",
        created_by_id=actor_id,
        expires_hours=payload.get("expires_hours", 168),
        max_uses=payload.get("max_uses", 50),
    )
    data = token.to_dict()
    data["token"] = raw  # shown once
    return created(data)


@bp.get("/enrollment-tokens")
@permission_required(AGENTS_MANAGE)
def list_enrollment_tokens():
    tokens = AgentEnrollmentToken.query.order_by(AgentEnrollmentToken.created_at.desc()).all()
    return success([t.to_dict() for t in tokens], meta={"count": len(tokens)})


@bp.post("/register")
def register():
    """Public enrollment — requires a valid enrollment token."""
    payload = request.get_json(silent=True) or {}
    result = agents_service.register_agent(
        enrollment_token=payload.get("enrollment_token"),
        hostname=payload.get("hostname"),
        name=payload.get("name"),
        agent_version=payload.get("agent_version"),
    )
    return created(result)


@bp.post("/pair")
def pair():
    """Public enrollment — 6-digit pairing code from Computers → Add device."""
    from uitop.services import pairing as pairing_svc

    payload = request.get_json(silent=True) or {}
    result = pairing_svc.pair_with_code(
        payload.get("code") or payload.get("pairing_code"),
        hostname=payload.get("hostname"),
        agent_version=payload.get("agent_version"),
    )
    return created(result)


@bp.post("/token")
def token():
    """Exchange agent client credentials for a JWT access token."""
    payload = request.get_json(silent=True) or {}
    result = agents_service.exchange_client_credentials(
        client_id=payload.get("client_id"),
        client_secret=payload.get("client_secret"),
    )
    return success(result)


@bp.post("/heartbeat")
@agent_scope_required(AGENTS_HEARTBEAT)
def heartbeat():
    payload = request.get_json(silent=True) or {}
    result = agents_service.heartbeat(g.agent_client, payload)
    return success(result)


@bp.post("/inventory")
@agent_scope_required(AGENTS_INVENTORY)
def inventory():
    payload = request.get_json(silent=True) or {}
    result = agents_service.upsert_inventory(g.agent_client, payload)
    return success(result)


@bp.post("/performance")
@agent_scope_required(AGENTS_PERFORMANCE)
def performance():
    payload = request.get_json(silent=True) or {}
    result = agents_service.ingest_performance(g.agent_client, payload)
    return success(result)


@bp.post("/events")
@agent_scope_required(AGENTS_EVENTS)
def events():
    payload = request.get_json(silent=True) or {}
    result = agents_service.ingest_events(g.agent_client, payload)
    return success(result)


@bp.post("/alerts")
@agent_scope_required(AGENTS_ALERTS)
def alerts():
    payload = request.get_json(silent=True) or {}
    result = agents_service.ingest_alerts(g.agent_client, payload)
    return success(result)


@bp.get("/commands")
@agent_scope_required(AGENTS_HEARTBEAT)
def list_pending_commands():
    """Agent polls for queued remote actions."""
    from uitop.services import agent_commands as cmd_svc

    rows = cmd_svc.claim_pending_commands(g.agent_client.agent_id)
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})


@bp.post("/commands/<int:command_id>/result")
@agent_scope_required(AGENTS_HEARTBEAT)
def command_result(command_id: int):
    from uitop.services import agent_commands as cmd_svc

    payload = request.get_json(silent=True) or {}
    row = cmd_svc.complete_command(
        command_id,
        agent_id=g.agent_client.agent_id,
        status=payload.get("status") or "completed",
        result=payload.get("result"),
    )
    return success(row.to_dict())
