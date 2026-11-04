"""Settings — admin-only platform control center."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from uitop.extensions import db
from uitop.models.audit import AuditLog
from uitop.models.settings import SystemSetting
from uitop.services.audit import log_audit
from uitop.services.computers_view import relative_time


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


DEFAULTS: dict[str, dict] = {
    "general": {
        "org_name": "Umzinyathi District Municipality",
        "timezone": "Africa/Johannesburg",
        "language": "English",
        "date_format": "DD/MM/YYYY",
        "logo_url": "",
    },
    "security": {
        "min_password_length": 12,
        "require_mfa": True,
        "session_timeout_minutes": 30,
        "lockout_attempts": 5,
        "ip_restriction_enabled": False,
        "trusted_cidrs": "",
    },
    "email": {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "smtp_encryption": "TLS",
        "smtp_username": "uitop@umzinyathi.gov.za",
        "smtp_password_set": False,
        "status": "Connected",
    },
    "notifications": {
        "email_alerts": True,
        "ticket_updates": True,
        "security_alerts": True,
        "maintenance_reminders": True,
    },
    "backup": {
        "backup_path": "D:/UITOP/Backups",
        "retention_days": 90,
        "cloud_enabled": False,
        "encryption": True,
        "last_backup": "Today 02:00",
    },
    "storage": {
        "usage_gb": 58,
        "quota_gb": 200,
        "repository_path": "D:/UITOP/Repository",
    },
    "monitoring": {
        "cpu_threshold": 90,
        "memory_threshold": 85,
        "disk_free_threshold": 10,
        "heartbeat_seconds": 60,
        "offline_minutes": 5,
    },
    "agents": {
        "auto_registration": True,
        "token_expiry_hours": 24,
        "max_token_uses": 1,
        "unattended_access": False,
    },
    "integrations": {
        "active_directory": False,
        "webhook_url": "",
        "teams_notifications": False,
    },
    "api": {
        "keys_enabled": True,
        "rate_limit_per_minute": 120,
    },
    "appearance": {
        "theme": "light",
        "primary_color": "Municipal Teal",
        "dashboard_layout": "expanded",
    },
    "system": {
        "app_version": "UITOP 1.0.0",
        "database_type": "SQLite",
        "system_health": "Healthy",
    },
}


CATEGORIES = [
    ("general", "General", "Organization name, timezone, language"),
    ("organization", "Organization", "Municipal profile and branding"),
    ("security", "Security", "Password policy, MFA, lockout"),
    ("authentication", "Authentication", "Sessions and sign-in rules"),
    ("email", "Email / SMTP", "Outbound mail configuration"),
    ("notifications", "Notifications", "Alert delivery preferences"),
    ("backup", "Backup & Restore", "Paths, retention, encryption"),
    ("storage", "Storage", "Repository and capacity"),
    ("monitoring", "Monitoring", "Alert thresholds and heartbeat"),
    ("agents", "Agents", "Enrollment and unattended access"),
    ("integrations", "Integrations", "AD, webhooks, connectors"),
    ("api", "API Keys", "API access and rate limits"),
    ("appearance", "Appearance", "Theme and layout"),
    ("system", "System", "Version, database, health"),
    ("audit", "Audit", "Recent settings changes"),
]


def ensure_schema() -> None:
    SystemSetting.__table__.create(db.engine, checkfirst=True)


def _get_row(key: str) -> SystemSetting | None:
    return SystemSetting.query.filter_by(key=key).first()


def get_category(category: str) -> dict:
    ensure_schema()
    key = category if category in DEFAULTS else _map_alias(category)
    defaults = deepcopy(DEFAULTS.get(key, {}))
    row = _get_row(key)
    if row and isinstance(row.value, dict):
        defaults.update(row.value)
    return defaults


def _map_alias(view: str) -> str:
    aliases = {
        "organization": "general",
        "authentication": "security",
    }
    return aliases.get(view, view if view in DEFAULTS else "general")


def get_all_settings() -> dict[str, dict]:
    ensure_schema()
    out = {}
    for key in DEFAULTS:
        out[key] = get_category(key)
    return out


def update_category(category: str, data: dict, *, actor_id: int | None = None) -> dict:
    ensure_schema()
    key = _map_alias(category)
    if key not in DEFAULTS:
        key = "general"
    current = get_category(key)
    old = deepcopy(current)
    # only accept known keys
    for k, v in data.items():
        if k in DEFAULTS[key] or k in current:
            if isinstance(DEFAULTS[key].get(k), bool):
                current[k] = v in (True, "1", "true", "on", "yes")
            elif isinstance(DEFAULTS[key].get(k), int):
                try:
                    current[k] = int(v)
                except (TypeError, ValueError):
                    pass
            else:
                current[k] = v

    row = _get_row(key)
    if row is None:
        row = SystemSetting(key=key, category=key, value=current)
        db.session.add(row)
    else:
        row.value = current
        row.category = key
    row.updated_by_id = actor_id
    row.updated_at = utcnow()
    db.session.commit()

    changed = {k: {"old": old.get(k), "new": current.get(k)} for k in current if old.get(k) != current.get(k)}
    if changed:
        log_audit(
            "settings.update",
            actor_user_id=actor_id,
            resource_type="settings",
            resource_id=key,
            meta={"result": "Success", "category": key, "changed": changed},
        )
    return current


def settings_audit(limit: int = 20) -> list[dict]:
    rows = (
        AuditLog.query.filter(AuditLog.action.like("settings.%"))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        actor = r.actor.full_name if r.actor else "System"
        meta = r.meta if isinstance(r.meta, dict) else {}
        detail = meta.get("category") or r.resource_id or "settings"
        changed = meta.get("changed") or {}
        summary = ", ".join(changed.keys()) if changed else detail
        out.append(
            {
                "when": r.created_at.strftime("%H:%M") if r.created_at else "—",
                "when_full": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "—",
                "actor": actor,
                "summary": f"{actor} updated {summary}",
                "rel": relative_time(r.created_at) if r.created_at else "—",
            }
        )
    return out


def build_module_payload(view: str = "general") -> dict:
    ensure_schema()
    all_s = get_all_settings()
    key = _map_alias(view)
    return {
        "categories": [{"id": c[0], "label": c[1], "desc": c[2]} for c in CATEGORIES],
        "settings": all_s,
        "current": all_s.get(key, all_s["general"]),
        "current_key": key,
        "view": view,
        "audit": settings_audit(),
        "system": all_s["system"] | {
            "storage_usage": f"{all_s['storage'].get('usage_gb', 0)} GB",
            "last_backup": all_s["backup"].get("last_backup", "—"),
        },
    }
