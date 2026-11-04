"""SNMP credential profiles for network / printer polling."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SnmpProfile(db.Model):
    __tablename__ = "snmp_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    version = db.Column(db.String(16), default="v2c", nullable=False)
    community = db.Column(db.String(120), nullable=False, default="public")
    scope = db.Column(db.String(120), nullable=True)
    is_write = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self, *, include_secret: bool = False):
        data = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "community": self.community if include_secret else (self.community[:2] + "•••" if self.community else "—"),
            "community_full": self.community if include_secret else None,
            "scope": self.scope or "—",
            "is_write": self.is_write,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        return data
