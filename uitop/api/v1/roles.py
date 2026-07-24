"""Roles API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import permission_required
from uitop.core.permissions import ROLES_MANAGE
from uitop.models.role import Permission
from uitop.schemas import created, success
from uitop.services import users as users_service

bp = Blueprint("roles", __name__, url_prefix="/roles")


@bp.get("")
@permission_required(ROLES_MANAGE)
def list_roles():
    roles = users_service.list_roles()
    return success([r.to_dict() for r in roles], meta={"count": len(roles)})


@bp.post("")
@permission_required(ROLES_MANAGE)
def create_role():
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    role = users_service.create_role(
        name=payload.get("name"),
        description=payload.get("description"),
        permission_codes=payload.get("permissions"),
        actor_id=actor_id,
    )
    return created(role.to_dict())


@bp.get("/permissions")
@permission_required(ROLES_MANAGE)
def list_permissions():
    perms = Permission.query.order_by(Permission.code).all()
    return success([p.to_dict() for p in perms], meta={"count": len(perms)})


@bp.patch("/<int:role_id>")
@permission_required(ROLES_MANAGE)
def update_role(role_id: int):
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    if "permissions" in payload:
        role = users_service.update_role_permissions(role_id, payload.get("permissions") or [], actor_id=actor_id)
    else:
        role = users_service.get_role_or_404(role_id)
        if "description" in payload:
            role.description = payload["description"]
            from uitop.extensions import db

            db.session.commit()
    return success(role.to_dict())
