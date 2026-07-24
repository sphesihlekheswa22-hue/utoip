"""Users API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import permission_required
from uitop.core.permissions import USERS_MANAGE
from uitop.models.user import User
from uitop.schemas import created, success
from uitop.services import users as users_service

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.get("")
@permission_required(USERS_MANAGE)
def list_users():
    users = User.query.order_by(User.email).all()
    return success([u.to_dict() for u in users], meta={"count": len(users)})


@bp.post("")
@permission_required(USERS_MANAGE)
def create_user():
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    user = users_service.create_user(
        email=payload.get("email"),
        password=payload.get("password"),
        full_name=payload.get("full_name"),
        role_names=payload.get("roles") or payload.get("role_names"),
        department_id=payload.get("department_id"),
        actor_id=actor_id,
    )
    return created(user.to_dict())


@bp.get("/<int:user_id>")
@permission_required(USERS_MANAGE)
def get_user(user_id: int):
    user = users_service.get_user_or_404(user_id)
    return success(user.to_dict())


@bp.patch("/<int:user_id>")
@permission_required(USERS_MANAGE)
def update_user(user_id: int):
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    user = users_service.update_user(user_id, payload, actor_id=actor_id)
    return success(user.to_dict())


@bp.put("/<int:user_id>/roles")
@permission_required(USERS_MANAGE)
def assign_roles(user_id: int):
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    role_names = payload.get("roles") or payload.get("role_names") or []
    user = users_service.assign_roles(user_id, role_names, actor_id=actor_id)
    return success(user.to_dict())
