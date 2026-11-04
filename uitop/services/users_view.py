"""Users — Identity & User Management Center (people, roles, assignments).

Infrastructure manages devices. Users manages people who use those devices.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from uitop.core.permissions import ALL_PERMISSIONS
from uitop.models.assets import Asset, AssetAssignment
from uitop.models.audit import AuditLog
from uitop.models.auth import RefreshToken
from uitop.models.department import Department
from uitop.models.helpdesk import Ticket
from uitop.models.role import Permission, Role
from uitop.models.user import User
from uitop.services import assets as asset_svc
from uitop.services import helpdesk as hd_svc
from uitop.services.computers_view import relative_time


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


ROLE_LABELS = {
    "super_admin": "Super Administrator",
    "admin": "IT Administrator",
    "operator": "Operator",
    "helpdesk": "Helpdesk",
    "employee": "Employee",
    "viewer": "Employee",  # legacy alias
    "agent": "Agent (Machine)",
}

ENTERPRISE_ROLE_CATALOG = [
    {"key": "super_admin", "name": "Super Admin", "desc": "Full platform access"},
    {"key": "admin", "name": "IT Administrator", "desc": "Municipal IT administration"},
    {"key": "network_admin", "name": "Network Administrator", "desc": "Network devices and availability"},
    {"key": "systems_admin", "name": "Systems Administrator", "desc": "Servers and infrastructure"},
    {"key": "helpdesk_manager", "name": "Help Desk Manager", "desc": "Ticket queues and SLA"},
    {"key": "technician", "name": "Technician", "desc": "Day-to-day support work"},
    {"key": "asset_manager", "name": "Asset Manager", "desc": "Asset lifecycle and assignments"},
    {"key": "security_officer", "name": "Security Officer", "desc": "Security posture and compliance"},
    {"key": "department_manager", "name": "Department Manager", "desc": "Department staff and requests"},
    {"key": "employee", "name": "Employee", "desc": "Standard end-user access"},
    {"key": "auditor", "name": "Auditor", "desc": "Read-only audit and reports"},
]


def role_label(name: str) -> str:
    return ROLE_LABELS.get(name, name.replace("_", " ").title())


def serialize_user(user: User) -> dict:
    roles = user.role_names()
    if user.is_super_admin:
        label = "Super Admin"
    elif roles:
        label = role_label(roles[0])
    else:
        label = "User"

    computer = primary_computer_for_user(user.id)
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "roles": roles,
        "role_label": label,
        "department": user.department.name if user.department else "—",
        "department_id": user.department_id,
        "is_active": user.is_active,
        "status": "Active" if user.is_active else "Inactive",
        "is_super_admin": user.is_super_admin,
        "mfa_enabled": user.mfa_enabled,
        "last_login": relative_time(user.last_login_at) if user.last_login_at else "Never",
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "permissions": user.permission_codes(),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "computer": computer["label"] if computer else "—",
        "computer_url": computer["url"] if computer else None,
        "locked": False,  # reserved for future lockout policy
    }


def primary_computer_for_user(user_id: int) -> dict | None:
    """Best-effort laptop/desktop from open assignment or custodianship."""
    assignment_ids = [
        a.asset_id
        for a in AssetAssignment.query.filter_by(user_id=user_id, returned_at=None).all()
    ]
    assets = []
    if assignment_ids:
        assets.extend(Asset.query.filter(Asset.id.in_(assignment_ids)).all())
    assets.extend(Asset.query.filter_by(custodian_user_id=user_id).all())
    seen = set()
    for asset in assets:
        if asset.id in seen:
            continue
        seen.add(asset.id)
        linked = asset_svc.linked_summary(asset)
        if linked and linked.get("type") == "computer":
            return {
                "label": linked.get("label") or asset.asset_tag or asset.name,
                "url": linked.get("url") or f"/assets/{asset.id}",
                "asset_id": asset.id,
            }
        if (asset.linked_type or "") == "computer":
            return {
                "label": asset.asset_tag or asset.name,
                "url": f"/assets/{asset.id}",
                "asset_id": asset.id,
            }
        cat = (asset.category.name if asset.category else "") or ""
        name = (asset.name or "").lower()
        if "laptop" in name or "desktop" in name or "computer" in cat.lower() or "pc" in name:
            return {
                "label": asset.asset_tag or asset.name,
                "url": f"/assets/{asset.id}",
                "asset_id": asset.id,
            }
    return None


def user_assets(user_id: int) -> list[dict]:
    assignment_ids = {
        a.asset_id
        for a in AssetAssignment.query.filter_by(user_id=user_id, returned_at=None).all()
    }
    rows = []
    seen = set()
    for asset in Asset.query.order_by(Asset.asset_tag).all():
        if asset.id in seen:
            continue
        if asset.id in assignment_ids or asset.custodian_user_id == user_id:
            seen.add(asset.id)
            data = asset_svc.serialize_asset(asset)
            data["url"] = f"/assets/{asset.id}"
            rows.append(data)
    return rows


def user_tickets(user_id: int) -> dict:
    assigned = hd_svc.list_tickets(assignee_user_id=user_id)
    requested_models = (
        Ticket.query.filter_by(requester_user_id=user_id)
        .order_by(Ticket.created_at.desc())
        .limit(100)
        .all()
    )
    requested = [hd_svc.serialize_ticket(t) for t in requested_models]
    open_n = sum(1 for t in requested + assigned if t.get("status") not in ("resolved", "closed", "cancelled"))
    resolved = sum(1 for t in requested + assigned if t.get("status") in ("resolved", "closed"))
    return {
        "assigned": assigned[:40],
        "requested": requested[:40],
        "open": open_n,
        "resolved": resolved,
        "avg_resolution": "—",
    }


def user_sessions(user_id: int) -> list[dict]:
    now = utcnow()
    rows = (
        RefreshToken.query.filter_by(user_id=user_id)
        .order_by(RefreshToken.created_at.desc())
        .limit(30)
        .all()
    )
    out = []
    for t in rows:
        expires = _as_utc(t.expires_at)
        active = t.revoked_at is None and (expires is None or expires > now)
        ua = t.user_agent or "Unknown device"
        device = "Mobile" if any(x in ua.lower() for x in ("mobile", "android", "iphone")) else "Desktop"
        if "edg" in ua.lower() or "chrome" in ua.lower() or "firefox" in ua.lower():
            client = "Browser"
        else:
            client = "App / API"
        out.append(
            {
                "id": t.id,
                "jti": t.jti,
                "device": device,
                "client": client,
                "user_agent": ua[:80],
                "ip": t.ip_address or "—",
                "created": relative_time(t.created_at),
                "expires": relative_time(t.expires_at) if t.expires_at else "—",
                "active": active,
                "status": "Active" if active else ("Revoked" if t.revoked_at else "Expired"),
            }
        )
    return out


def user_activity(user_id: int, limit: int = 40) -> list[dict]:
    rows = (
        AuditLog.query.filter_by(actor_user_id=user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [a.to_dict() for a in rows]


def user_documents(user_id: int) -> list[dict]:
    try:
        from uitop.models.files import RepoFile

        files = (
            RepoFile.query.filter_by(owner_user_id=user_id)
            .order_by(RepoFile.updated_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "id": f.id,
                "name": f.title or f.original_name or f.filename,
                "url": f"/documents/{f.id}",
                "updated": relative_time(f.updated_at),
            }
            for f in files
        ]
    except Exception:
        return []


def user_software_hint(user_id: int) -> list[dict]:
    """Demo / derived software availability for the profile (catalog snapshot)."""
    # Prefer licenses or installed software later; for now show common municipal suite
    base = [
        {"name": "Microsoft 365", "status": "Assigned"},
        {"name": "Microsoft Teams", "status": "Assigned"},
        {"name": "Google Chrome", "status": "Available"},
        {"name": "Adobe Acrobat", "status": "Request"},
    ]
    return base


def build_user_profile(user_id: int) -> dict:
    user = User.query.get(user_id)
    if user is None:
        return {}
    data = serialize_user(user)
    assets = user_assets(user_id)
    tickets = user_tickets(user_id)
    sessions = user_sessions(user_id)
    activity = user_activity(user_id)
    docs = user_documents(user_id)
    history = _build_history(user, activity, assets)
    return {
        "user": data,
        "overview": {
            "position": "—",
            "phone": "—",
            "manager": "—",
            "extension": "—",
        },
        "assets": assets,
        "tickets": tickets,
        "software": user_software_hint(user_id),
        "permissions": _group_permissions(data["permissions"]),
        "sessions": sessions,
        "activity": activity,
        "documents": docs,
        "history": history,
        "ai_insights": _user_ai_insights(data, tickets, sessions),
    }


def _group_permissions(codes: list[str]) -> list[dict]:
    groups: dict[str, list[str]] = defaultdict(list)
    desc_map = {c: d for c, d in ALL_PERMISSIONS}
    for code in codes:
        module = code.split(":")[0].replace("_", " ").title() if ":" in code else "General"
        action = code.split(":")[-1] if ":" in code else code
        groups[module].append(f"{action} — {desc_map.get(code, code)}")
    return [{"module": m, "entries": items} for m, items in sorted(groups.items())]


def _build_history(user: User, activity: list[dict], assets: list[dict]) -> list[dict]:
    events = []
    if user.created_at:
        events.append(
            {
                "when": user.created_at.strftime("%Y-%m-%d"),
                "title": "Joined UITOP",
                "detail": f"Account created for {user.email}",
            }
        )
    for a in assets[:5]:
        events.append(
            {
                "when": "Assigned",
                "title": f"Asset linked: {a.get('asset_tag') or a.get('name')}",
                "detail": a.get("status_label") or a.get("status") or "",
            }
        )
    for row in activity[:10]:
        events.append(
            {
                "when": (row.get("created_at") or "")[:16].replace("T", " "),
                "title": row.get("action") or "Event",
                "detail": f"{row.get('resource_type') or ''} {row.get('resource_id') or ''}".strip(),
            }
        )
    return events[:20]


def _user_ai_insights(user: dict, tickets: dict, sessions: list[dict]) -> list[dict]:
    tips = []
    if tickets["open"] >= 3:
        tips.append(
            {
                "tone": "warning",
                "title": "Open ticket load",
                "body": f"{user['full_name']} has {tickets['open']} open tickets linked as requester or assignee.",
            }
        )
    if user["last_login"] == "Never":
        tips.append(
            {
                "tone": "warning",
                "title": "Never logged in",
                "body": "Recommend sending an invitation or verifying the account is needed.",
            }
        )
    active_sessions = sum(1 for s in sessions if s["active"])
    if active_sessions > 3:
        tips.append(
            {
                "tone": "accent",
                "title": "Multiple active sessions",
                "body": f"{active_sessions} active refresh sessions — review for shared credentials.",
            }
        )
    if not tips:
        tips.append(
            {
                "tone": "success",
                "title": "Account healthy",
                "body": f"{user['full_name']} is {user['status'].lower()} with role {user['role_label']}.",
            }
        )
    return tips


def identity_kpis() -> dict:
    users = User.query.all()
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_month = sum(1 for u in users if u.created_at and _as_utc(u.created_at) >= month_start)
    admins = sum(
        1
        for u in users
        if u.is_super_admin or "admin" in u.role_names() or "super_admin" in u.role_names()
    )
    active_sessions = RefreshToken.query.filter(
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > now,
    ).count()
    return {
        "total": len(users),
        "active": sum(1 for u in users if u.is_active),
        "inactive": sum(1 for u in users if not u.is_active),
        "admins": admins,
        "locked": 0,
        "new_month": new_month,
        "sessions": active_sessions,
        "departments": Department.query.count(),
        "roles": Role.query.count(),
    }


def department_rows() -> list[dict]:
    out = []
    for d in Department.query.order_by(Department.name).all():
        count = User.query.filter_by(department_id=d.id).count()
        out.append(
            {
                "id": d.id,
                "name": d.name,
                "code": d.code or "—",
                "description": d.description or "",
                "users": count,
            }
        )
    return out


def role_rows() -> list[dict]:
    out = []
    for r in Role.query.order_by(Role.name).all():
        out.append(
            {
                "id": r.id,
                "name": r.name,
                "label": role_label(r.name),
                "description": r.description or ROLE_LABELS.get(r.name, ""),
                "is_system": r.is_system,
                "users": r.users.count() if hasattr(r.users, "count") else len(list(r.users)),
                "permissions": r.permission_codes(),
                "perm_count": len(r.permission_codes()),
            }
        )
    return out


def permission_matrix() -> list[dict]:
    """Group ALL_PERMISSIONS by module for the Permissions view."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for code, desc in ALL_PERMISSIONS:
        module = code.split(":")[0]
        groups[module].append({"code": code, "action": code.split(":")[-1], "description": desc})
    return [{"module": m.replace("_", " ").title(), "key": m, "entries": items} for m, items in sorted(groups.items())]


def demo_teams() -> list[dict]:
    return [
        {
            "id": "net",
            "name": "Network Team",
            "members": 4,
            "lead": "Network Administrator",
            "focus": "Switches, firewalls, WAN",
        },
        {
            "id": "desk",
            "name": "Desktop Support",
            "members": 8,
            "lead": "Help Desk Manager",
            "focus": "Endpoints and printers",
        },
        {
            "id": "srv",
            "name": "Server Team",
            "members": 3,
            "lead": "Systems Administrator",
            "focus": "Servers and virtualization",
        },
        {
            "id": "sec",
            "name": "Security Team",
            "members": 2,
            "lead": "Security Officer",
            "focus": "Posture and incidents",
        },
        {
            "id": "infra",
            "name": "Infrastructure Team",
            "members": 5,
            "lead": "IT Administrator",
            "focus": "Cross-cutting estate work",
        },
    ]


def all_assignments() -> list[dict]:
    rows = []
    for u in User.query.filter_by(is_active=True).order_by(User.full_name).limit(80).all():
        assets = user_assets(u.id)
        computer = primary_computer_for_user(u.id)
        rows.append(
            {
                "user_id": u.id,
                "full_name": u.full_name,
                "department": u.department.name if u.department else "—",
                "computer": computer["label"] if computer else "—",
                "computer_url": computer["url"] if computer else None,
                "asset_count": len(assets),
                "assets": [a.get("asset_tag") or a.get("name") for a in assets[:4]],
            }
        )
    return rows


def active_sessions_global() -> list[dict]:
    now = utcnow()
    tokens = (
        RefreshToken.query.filter(RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
        .order_by(RefreshToken.created_at.desc())
        .limit(50)
        .all()
    )
    out = []
    for t in tokens:
        user = t.user
        ua = t.user_agent or "Unknown"
        out.append(
            {
                "id": t.id,
                "user_id": t.user_id,
                "user_name": user.full_name if user else f"User #{t.user_id}",
                "email": user.email if user else "—",
                "ip": t.ip_address or "—",
                "device": "Mobile" if "mobile" in ua.lower() else "Desktop",
                "created": relative_time(t.created_at),
                "user_agent": ua[:60],
            }
        )
    return out


def audit_rows(limit: int = 40) -> list[dict]:
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    out = []
    for a in rows:
        d = a.to_dict()
        actor = User.query.get(a.actor_user_id) if a.actor_user_id else None
        d["actor_name"] = actor.full_name if actor else "System"
        out.append(d)
    return out


def invitations() -> list[dict]:
    return [
        {
            "email": "new.hire@umzinyathi.gov.za",
            "role": "Employee",
            "department": "Corporate Services",
            "status": "Pending",
            "sent": "2026-07-20",
        },
        {
            "email": "contractor.it@umzinyathi.gov.za",
            "role": "Technician",
            "department": "IT",
            "status": "Accepted",
            "sent": "2026-07-12",
        },
        {
            "email": "auditor@umzinyathi.gov.za",
            "role": "Auditor",
            "department": "Office of the MM",
            "status": "Expired",
            "sent": "2026-06-01",
        },
    ]


def build_module_payload() -> dict:
    users = [serialize_user(u) for u in User.query.order_by(User.full_name).all()]
    kpis = identity_kpis()
    return {
        "kpis": kpis,
        "users": users,
        "departments": department_rows(),
        "roles": role_rows(),
        "enterprise_roles": ENTERPRISE_ROLE_CATALOG,
        "permissions": permission_matrix(),
        "teams": demo_teams(),
        "assignments": all_assignments(),
        "sessions": active_sessions_global(),
        "audit": audit_rows(),
        "invitations": invitations(),
        "ai_insights": _hub_ai_insights(users, kpis),
    }


def _hub_ai_insights(users: list[dict], kpis: dict) -> list[dict]:
    never = [u for u in users if u["last_login"] == "Never" and u["is_active"]]
    tips = []
    if never:
        tips.append(
            {
                "tone": "warning",
                "title": "Accounts never used",
                "body": f"{len(never)} active user(s) have never logged in. Review for disable or invitation resend.",
            }
        )
    if kpis["inactive"]:
        tips.append(
            {
                "tone": "accent",
                "title": "Inactive accounts",
                "body": f"{kpis['inactive']} inactive account(s) remain in the directory.",
            }
        )
    tips.append(
        {
            "tone": "success",
            "title": "Directory pulse",
            "body": f"{kpis['active']} active of {kpis['total']} users across {kpis['departments']} departments.",
        }
    )
    return tips
