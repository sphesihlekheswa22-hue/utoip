"""Auth-related models: refresh tokens and agent enrollment."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    replaced_by_jti = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)

    user = db.relationship("User", backref=db.backref("refresh_tokens", lazy="dynamic"))

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "jti": self.jti,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentEnrollmentToken(db.Model):
    __tablename__ = "agent_enrollment_tokens"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(120), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    token_prefix = db.Column(db.String(12), nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    max_uses = db.Column(db.Integer, nullable=True)
    use_count = db.Column(db.Integer, default=0, nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    created_by = db.relationship("User")

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        expires = _as_utc(self.expires_at)
        if expires and expires < utcnow():
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "token_prefix": self.token_prefix,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
