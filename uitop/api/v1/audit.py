"""Audit log API."""
from flask import Blueprint, request

from uitop.core.decorators import permission_required
from uitop.core.permissions import AUDIT_READ
from uitop.models.audit import AuditLog
from uitop.schemas import success

bp = Blueprint("audit", __name__, url_prefix="/audit")


@bp.get("")
@permission_required(AUDIT_READ)
def list_audit():
    query = AuditLog.query.order_by(AuditLog.created_at.desc())

    action = request.args.get("action")
    resource_type = request.args.get("resource_type")
    actor_user_id = request.args.get("actor_user_id", type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)

    if action:
        query = query.filter_by(action=action)
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    if actor_user_id:
        query = query.filter_by(actor_user_id=actor_user_id)

    rows = query.limit(limit).all()
    return success([r.to_dict() for r in rows], meta={"count": len(rows), "limit": limit})
