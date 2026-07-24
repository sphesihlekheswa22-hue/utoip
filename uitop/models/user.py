"""User model."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db
from uitop.models.role import user_roles


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = db.relationship("Department", back_populates="users")
    roles = db.relationship(
        "Role",
        secondary=user_roles,
        lazy="joined",
        backref=db.backref("users", lazy="dynamic"),
    )

    def role_names(self) -> list[str]:
        return sorted({r.name for r in self.roles})

    def permission_codes(self) -> list[str]:
        if self.is_super_admin:
            from uitop.core.permissions import ALL_PERMISSIONS

            return [code for code, _ in ALL_PERMISSIONS]
        codes: set[str] = set()
        for role in self.roles:
            codes.update(role.permission_codes())
        return sorted(codes)

    def has_permission(self, code: str) -> bool:
        if self.is_super_admin:
            return True
        return code in self.permission_codes()

    def to_dict(self, include_roles: bool = True):
        data = {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_super_admin": self.is_super_admin,
            "department_id": self.department_id,
            "department": self.department.to_dict() if self.department else None,
            "mfa_enabled": self.mfa_enabled,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "permissions": self.permission_codes(),
        }
        if include_roles:
            data["roles"] = [r.to_dict(include_permissions=False) for r in self.roles]
        return data
