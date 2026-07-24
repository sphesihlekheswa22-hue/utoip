"""Departments API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import permission_required
from uitop.core.permissions import DEPARTMENTS_MANAGE
from uitop.schemas import created, success
from uitop.services import users as users_service

bp = Blueprint("departments", __name__, url_prefix="/departments")


@bp.get("")
@permission_required(DEPARTMENTS_MANAGE)
def list_departments():
    depts = users_service.list_departments()
    return success([d.to_dict() for d in depts], meta={"count": len(depts)})


@bp.post("")
@permission_required(DEPARTMENTS_MANAGE)
def create_department():
    payload = request.get_json(silent=True) or {}
    actor_id = int(get_jwt_identity())
    dept = users_service.create_department(
        name=payload.get("name"),
        code=payload.get("code"),
        description=payload.get("description"),
        actor_id=actor_id,
    )
    return created(dept.to_dict())
