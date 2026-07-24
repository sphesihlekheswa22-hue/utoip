"""Auth API routes."""
from flask import request
from flask_jwt_extended import get_jwt_identity

from uitop.core.decorators import jwt_required_active
from uitop.core.errors import ValidationError
from uitop.models.user import User
from uitop.schemas import success
from uitop.services import auth as auth_service

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    result = auth_service.login(payload.get("email"), payload.get("password"))
    return success(result)


@bp.post("/refresh")
def refresh():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        # Also accept Authorization Bearer refresh
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:]
    result = auth_service.refresh_access_token(refresh_token)
    return success(result)


@bp.post("/logout")
@jwt_required_active
def logout():
    payload = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    auth_service.logout(refresh_token=payload.get("refresh_token"), user_id=user_id)
    return success({"logged_out": True})


@bp.get("/me")
@jwt_required_active
def me():
    user = User.query.get(int(get_jwt_identity()))
    if user is None:
        raise ValidationError("User not found")
    return success(user.to_dict())
