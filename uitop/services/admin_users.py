"""Resolve the primary super-admin user for demo/seed operations."""
from __future__ import annotations

from uitop.models.user import User


def first_super_admin() -> User | None:
    return User.query.filter_by(is_super_admin=True).order_by(User.id.asc()).first()
