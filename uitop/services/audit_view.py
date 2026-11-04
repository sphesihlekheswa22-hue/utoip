"""Audit Logs — read-only security & compliance console (platform black box)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from uitop.models.audit import AuditLog
from uitop.models.user import User
from uitop.services.computers_view import relative_time


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# action prefix → category
CATEGORY_MAP = {
    "auth": "Authentication",
    "users": "Users",
    "roles": "Users",
    "computers": "Infrastructure",
    "servers": "Infrastructure",
    "network": "Infrastructure",
    "printers": "Infrastructure",
    "agents": "Infrastructure",
    "assets": "Assets",
    "helpdesk": "Help Desk",
    "tickets": "Help Desk",
    "security": "Security",
    "settings": "Settings",
    "maintenance": "Maintenance",
    "files": "Documents",
    "documents": "Documents",
    "remote": "Remote Actions",
}


def classify_action(action: str) -> str:
    prefix = (action or "").split(".", 1)[0].lower()
    return CATEGORY_MAP.get(prefix, "System")


def derive_severity(action: str, meta: dict | None = None) -> str:
    a = (action or "").lower()
    meta = meta or {}
    if meta.get("severity"):
        return str(meta["severity"]).lower()
    if "fail" in a or "denied" in a or "lock" in a:
        return "high"
    if any(x in a for x in ("delete", "dispose", "revoke", "disable", "remote", "restart", "script")):
        return "high"
    if any(x in a for x in ("update", "assign", "role", "permission", "settings", "create")):
        return "medium"
    if "login" in a or "logout" in a or "refresh" in a:
        return "low"
    return "info"


def derive_result(action: str, meta: dict | None = None) -> str:
    meta = meta or {}
    if meta.get("result"):
        return str(meta["result"]).title()
    a = (action or "").lower()
    if "fail" in a or "denied" in a:
        return "Failed"
    return "Success"


def event_code(row_id: int) -> str:
    return f"AUD-{row_id:06d}"


def serialize_event(row: AuditLog) -> dict:
    actor = row.actor
    meta = row.meta if isinstance(row.meta, dict) else {}
    action = row.action or ""
    resource = "—"
    if row.resource_type:
        resource = row.resource_type
        if row.resource_id:
            resource = f"{row.resource_type} #{row.resource_id}"
    related_url = _related_url(row.resource_type, row.resource_id)
    return {
        "id": row.id,
        "code": event_code(row.id),
        "action": action,
        "action_label": action.replace(".", " · ").replace("_", " ").title(),
        "category": classify_action(action),
        "severity": derive_severity(action, meta),
        "result": derive_result(action, meta),
        "resource": resource,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "related_url": related_url,
        "actor_id": row.actor_user_id,
        "actor_name": actor.full_name if actor else (row.actor_client_id or "System"),
        "actor_email": actor.email if actor else "—",
        "ip": row.ip_address or "—",
        "user_agent": row.user_agent or "—",
        "meta": meta,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "when": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "—",
        "when_rel": relative_time(row.created_at) if row.created_at else "—",
    }


def _related_url(resource_type: str | None, resource_id: str | None) -> str | None:
    if not resource_type or not resource_id:
        return None
    try:
        rid = int(resource_id)
    except (TypeError, ValueError):
        return None
    mapping = {
        "user": f"/users/{rid}",
        "ticket": f"/helpdesk/{rid}",
        "asset": f"/assets/{rid}",
        "computer": f"/computers/{rid}",
        "server": f"/servers/{rid}",
        "work_order": f"/maintenance/{rid}",
    }
    return mapping.get(resource_type)


def query_events(
    *,
    category: str = "",
    severity: str = "",
    result: str = "",
    actor_id: int | None = None,
    q: str = "",
    days: int | None = 30,
    limit: int = 200,
) -> list[dict]:
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    if days:
        since = utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= since)
    if actor_id:
        query = query.filter_by(actor_user_id=actor_id)
    rows = query.limit(min(limit, 500)).all()
    events = [serialize_event(r) for r in rows]
    if category:
        events = [e for e in events if e["category"].lower() == category.lower()]
    if severity:
        events = [e for e in events if e["severity"] == severity.lower()]
    if result:
        events = [e for e in events if e["result"].lower() == result.lower()]
    if q:
        ql = q.lower()
        events = [
            e
            for e in events
            if ql in e["action"].lower()
            or ql in e["actor_name"].lower()
            or ql in e["resource"].lower()
            or ql in e["ip"].lower()
            or ql in e["code"].lower()
        ]
    return events


def audit_kpis() -> dict:
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    today = AuditLog.query.filter(AuditLog.created_at >= today_start).count()
    yesterday = AuditLog.query.filter(
        AuditLog.created_at >= yesterday_start,
        AuditLog.created_at < today_start,
    ).count()
    recent = [serialize_event(r) for r in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(300).all()]
    failed = sum(1 for e in recent if e["result"] == "Failed" or "fail" in e["action"].lower())
    config = sum(1 for e in recent if e["category"] == "Settings" or "settings" in e["action"].lower())
    critical = sum(1 for e in recent if e["severity"] == "high")
    delta = 0
    if yesterday:
        delta = int(round(100 * (today - yesterday) / yesterday))
    elif today:
        delta = 100
    return {
        "events_today": today,
        "delta_pct": delta,
        "failed_logins": failed,
        "config_changes": config,
        "critical": critical,
        "total": AuditLog.query.count(),
    }


def get_event(event_id: int) -> dict | None:
    row = AuditLog.query.get(event_id)
    if row is None:
        return None
    return serialize_event(row)


def to_csv(events: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Event ID", "Time", "User", "Email", "Action", "Category", "Resource", "Result", "Severity", "IP"])
    for e in events:
        writer.writerow(
            [
                e["code"],
                e["when"],
                e["actor_name"],
                e["actor_email"],
                e["action"],
                e["category"],
                e["resource"],
                e["result"],
                e["severity"],
                e["ip"],
            ]
        )
    return buf.getvalue()


def ensure_sample_events(*, actor_id: int | None = None) -> int:
    """Seed a few illustrative events when the log is empty (demo polish)."""
    if AuditLog.query.count() > 0:
        return 0
    from uitop.services.audit import log_audit

    samples = [
        ("auth.login", "user", actor_id, {"result": "Success"}),
        ("auth.login_failed", "authentication", None, {"result": "Failed", "severity": "high", "email": "jsmith@example.com"}),
        ("users.create", "user", actor_id, {"result": "Success"}),
        ("helpdesk.close", "ticket", "1024", {"result": "Success", "ticket": "HD-1024"}),
        ("remote.restart", "computer", "PC-101", {"result": "Success", "severity": "high", "reason": "Printer troubleshooting", "agent_version": "1.0.0"}),
        ("settings.update", "settings", "smtp", {"result": "Success", "key": "smtp.host", "old": "mail.local", "new": "smtp.office365.com"}),
        ("security.policy_change", "security", "firewall", {"result": "Success", "severity": "high"}),
        ("assets.assign", "asset", "12", {"result": "Success"}),
    ]
    n = 0
    for action, rtype, rid, meta in samples:
        log_audit(
            action,
            actor_user_id=actor_id,
            resource_type=rtype,
            resource_id=rid,
            meta=meta,
        )
        n += 1
    return n


def build_module_payload(
    *,
    category: str = "",
    severity: str = "",
    result: str = "",
    actor_id: int | None = None,
    q: str = "",
    days: int = 30,
) -> dict:
    events = query_events(
        category=category,
        severity=severity,
        result=result,
        actor_id=actor_id,
        q=q,
        days=days,
        limit=200,
    )
    users = [
        {"id": u.id, "name": u.full_name}
        for u in User.query.order_by(User.full_name).limit(80).all()
    ]
    categories = sorted(set(CATEGORY_MAP.values()) | {"System"})
    return {
        "kpis": audit_kpis(),
        "events": events,
        "failed": [e for e in events if e["result"] == "Failed"][:40],
        "config": [e for e in events if e["category"] == "Settings"][:40],
        "critical": [e for e in events if e["severity"] == "high"][:40],
        "filters": {
            "categories": categories,
            "severities": ["high", "medium", "low", "info"],
            "results": ["Success", "Failed"],
            "users": users,
            "days": days,
            "category": category,
            "severity": severity,
            "result": result,
            "actor_id": actor_id or "",
            "q": q,
        },
        "categories_legend": [
            {"name": "Authentication", "examples": "Login, logout, failed login, password reset"},
            {"name": "Users", "examples": "Create user, disable account, role change"},
            {"name": "Infrastructure", "examples": "Computer added, server removed, agent registered"},
            {"name": "Help Desk", "examples": "Ticket assigned, closed, reopened"},
            {"name": "Security", "examples": "Firewall disabled, policy changed"},
            {"name": "Settings", "examples": "SMTP changed, backup path updated"},
            {"name": "Remote Actions", "examples": "Restart PC, run script, remote session"},
        ],
    }
