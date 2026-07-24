"""Audit logging service."""
from __future__ import annotations

from flask import request

from uitop.extensions import db
from uitop.models.audit import AuditLog


def log_audit(
    action: str,
    *,
    actor_user_id: int | None = None,
    actor_client_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_client_id=actor_client_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=request.remote_addr if request else None,
        user_agent=(request.headers.get("User-Agent")[:255] if request and request.headers.get("User-Agent") else None),
        meta=meta,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
