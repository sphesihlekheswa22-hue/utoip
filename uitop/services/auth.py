"""Authentication service: login, refresh, logout."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from flask import current_app, request
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token, get_jti

from uitop.core.errors import UnauthorizedError, ValidationError
from uitop.core.security import hash_secret, verify_password, verify_secret
from uitop.extensions import db
from uitop.models.auth import RefreshToken
from uitop.models.user import User
from uitop.services.audit import log_audit


def utcnow():
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _claims_for_user(user: User) -> dict:
    return {
        "roles": user.role_names(),
        "permissions": user.permission_codes(),
        "is_super_admin": user.is_super_admin,
        "email": user.email,
        "full_name": user.full_name,
    }


def authenticate(email: str, password: str) -> User:
    if not email or not password:
        raise ValidationError("Email and password are required")
    user = User.query.filter_by(email=email.strip().lower()).first()
    if user is None or not verify_password(user.password_hash, password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    return user


def issue_tokens(user: User) -> dict:
    claims = _claims_for_user(user)
    access = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user.id), additional_claims={"type": "refresh"})
    decoded = decode_token(refresh)
    jti = decoded["jti"]
    exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

    record = RefreshToken(
        user_id=user.id,
        jti=jti,
        token_hash=hash_secret(refresh),
        expires_at=exp,
        user_agent=(request.headers.get("User-Agent") or "")[:255] if request else None,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(record)
    user.last_login_at = utcnow()
    db.session.commit()

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }


def login(email: str, password: str) -> dict:
    user = authenticate(email, password)
    tokens = issue_tokens(user)
    log_audit("auth.login", actor_user_id=user.id, resource_type="user", resource_id=user.id)
    return {"user": user.to_dict(), "tokens": tokens}


def refresh_access_token(refresh_token: str) -> dict:
    if not refresh_token:
        raise ValidationError("refresh_token is required")
    try:
        decoded = decode_token(refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid refresh token") from exc

    jti = decoded.get("jti")
    identity = decoded.get("sub")
    record = RefreshToken.query.filter_by(jti=jti).first()
    if record is None or record.is_revoked:
        raise UnauthorizedError("Refresh token revoked or unknown")
    if _as_utc(record.expires_at) < utcnow():
        raise UnauthorizedError("Refresh token expired")
    if not verify_secret(record.token_hash, refresh_token):
        raise UnauthorizedError("Invalid refresh token")

    user = User.query.get(int(identity))
    if user is None or not user.is_active:
        raise UnauthorizedError("User inactive or not found")

    # Rotate refresh token
    record.revoked_at = utcnow()
    new_tokens = issue_tokens(user)
    new_jti = get_jti(new_tokens["refresh_token"])
    record.replaced_by_jti = new_jti
    db.session.commit()

    log_audit("auth.refresh", actor_user_id=user.id, resource_type="user", resource_id=user.id)
    return {"tokens": new_tokens}


def logout(refresh_token: str | None = None, user_id: int | None = None) -> None:
    if refresh_token:
        try:
            decoded = decode_token(refresh_token)
            jti = decoded.get("jti")
            record = RefreshToken.query.filter_by(jti=jti).first()
            if record and not record.is_revoked:
                record.revoked_at = utcnow()
                db.session.commit()
        except Exception:  # noqa: BLE001
            pass
    elif user_id:
        RefreshToken.query.filter_by(user_id=user_id, revoked_at=None).update(
            {"revoked_at": utcnow()},
            synchronize_session=False,
        )
        db.session.commit()

    if user_id:
        log_audit("auth.logout", actor_user_id=user_id, resource_type="user", resource_id=user_id)


def generate_opaque_token(prefix: str = "uitop", nbytes: int = 24) -> str:
    return f"{prefix}_{secrets.token_urlsafe(nbytes)}"
