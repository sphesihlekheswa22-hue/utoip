"""RBAC decorators for API routes."""
from __future__ import annotations

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from uitop.core.errors import ForbiddenError, UnauthorizedError
from uitop.models.api_client import ApiClient
from uitop.models.user import User


def jwt_required_active(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("token_use") == "agent":
            raise UnauthorizedError("User access token required")
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id)) if user_id is not None else None
        if user is None or not user.is_active:
            raise UnauthorizedError("User is inactive or not found")
        return fn(*args, **kwargs)

    return wrapper


def permission_required(*permissions: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("token_use") == "agent":
                raise ForbiddenError("User permissions required")
            user_perms = set(claims.get("permissions") or [])
            if claims.get("is_super_admin"):
                return fn(*args, **kwargs)
            missing = [p for p in permissions if p not in user_perms]
            if missing:
                raise ForbiddenError(
                    "Missing required permission(s)",
                    details={"required": list(permissions), "missing": missing},
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def role_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("token_use") == "agent":
                raise ForbiddenError("User role required")
            user_roles = set(claims.get("roles") or [])
            if claims.get("is_super_admin"):
                return fn(*args, **kwargs)
            if not user_roles.intersection(roles):
                raise ForbiddenError(
                    "Missing required role(s)",
                    details={"required": list(roles)},
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user() -> User | None:
    verify_jwt_in_request(optional=True)
    identity = get_jwt_identity()
    if identity is None:
        return None
    claims = get_jwt() or {}
    if claims.get("token_use") == "agent":
        return None
    return User.query.get(int(identity))


def current_api_client() -> ApiClient | None:
    if getattr(g, "agent_client", None) is not None:
        return g.agent_client
    verify_jwt_in_request(optional=True)
    claims = get_jwt() or {}
    if claims.get("token_use") != "agent":
        return None
    client_id = get_jwt_identity()
    if not client_id:
        return None
    return ApiClient.query.filter_by(client_id=client_id, is_active=True).first()


def agent_required(fn):
    """Require a valid agent access JWT tied to an active ApiClient."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("token_use") != "agent":
            raise UnauthorizedError("Agent access token required")
        client_id = get_jwt_identity()
        client = ApiClient.query.filter_by(client_id=client_id).first()
        if client is None or not client.is_active:
            raise UnauthorizedError("Agent client is inactive or not found")
        g.agent_client = client
        return fn(*args, **kwargs)

    return wrapper


def agent_scope_required(*scopes: str):
    """Require agent JWT with all listed scopes."""

    def decorator(fn):
        @wraps(fn)
        @agent_required
        def wrapper(*args, **kwargs):
            client: ApiClient = g.agent_client
            claims = get_jwt()
            token_scopes = set(claims.get("scopes") or client.scopes or [])
            missing = [s for s in scopes if s not in token_scopes]
            if missing:
                raise ForbiddenError(
                    "Missing required agent scope(s)",
                    details={"required": list(scopes), "missing": missing},
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
