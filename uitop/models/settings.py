"""System settings model — key/value platform configuration."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value = db.Column(db.JSON, nullable=True)
    category = db.Column(db.String(64), nullable=False, default="general", index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    updated_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by_id": self.updated_by_id,
        }
