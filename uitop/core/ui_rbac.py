"""UI RBAC — map web routes and sidebar modules to permission codes."""
from __future__ import annotations

from flask import session

from uitop.core.permissions import (
    ANALYSIS_READ,
    ASSETS_ASSIGN,
    ASSETS_DISPOSE,
    ASSETS_READ,
    ASSETS_WRITE,
    AUDIT_READ,
    BACKUP_MANAGE,
    BACKUP_READ,
    CALENDAR_READ,
    COMPUTERS_READ,
    COMPUTERS_WRITE,
    DASHBOARD_READ,
    DEPARTMENTS_MANAGE,
    FILES_MANAGE,
    FILES_READ,
    FILES_WRITE,
    HELPDESK_ASSIGN,
    HELPDESK_READ,
    HELPDESK_WRITE,
    LICENSES_READ,
    LICENSES_WRITE,
    MAINTENANCE_READ,
    MAINTENANCE_WRITE,
    MONITORING_READ,
    NETWORK_READ,
    NETWORK_WRITE,
    PRINTERS_READ,
    PRINTERS_WRITE,
    REPORTS_GENERATE,
    REPORTS_READ,
    ROLES_MANAGE,
    SECURITY_READ,
    SECURITY_WRITE,
    SERVERS_READ,
    SERVERS_WRITE,
    SETTINGS_MANAGE,
    SOFTWARE_READ,
    SOFTWARE_WRITE,
    USERS_MANAGE,
    VENDORS_READ,
    VENDORS_WRITE,
)

# Blueprint name → permission required for any access (GET included)
BLUEPRINT_READ: dict[str, str] = {
    "dashboard": DASHBOARD_READ,
    "monitoring": MONITORING_READ,
    "computers": COMPUTERS_READ,
    "servers": SERVERS_READ,
    "network": NETWORK_READ,
    "printers": PRINTERS_READ,
    "assets": ASSETS_READ,
    "software": SOFTWARE_READ,
    "licenses": LICENSES_READ,
    "vendors": VENDORS_READ,
    "backup": BACKUP_READ,
    "restore": BACKUP_READ,
    "files": FILES_READ,
    "documents": FILES_READ,
    "workspace": FILES_READ,
    "workflows": DASHBOARD_READ,
    "tasks": DASHBOARD_READ,
    "catalog": DASHBOARD_READ,
    "helpdesk": HELPDESK_READ,
    "maintenance": MAINTENANCE_READ,
    "calendar": CALENDAR_READ,
    "security": SECURITY_READ,
    "analysis": ANALYSIS_READ,
    "analytics": ANALYSIS_READ,
    "reports": REPORTS_READ,
    "ai": DASHBOARD_READ,  # IT Copilot — any logged-in ops user
    "profile": DASHBOARD_READ,  # My Profile — current user account hub
    "notifications": DASHBOARD_READ,
    "employee": DASHBOARD_READ,
    "users": USERS_MANAGE,
    "settings": SETTINGS_MANAGE,
    "audit": AUDIT_READ,
}

# Blueprint name → permission for mutating methods (POST/PUT/PATCH/DELETE)
BLUEPRINT_WRITE: dict[str, str] = {
    "computers": COMPUTERS_WRITE,
    "servers": SERVERS_WRITE,
    "network": NETWORK_WRITE,
    "printers": PRINTERS_WRITE,
    "assets": ASSETS_WRITE,
    "software": SOFTWARE_WRITE,
    "licenses": LICENSES_WRITE,
    "vendors": VENDORS_WRITE,
    "backup": BACKUP_MANAGE,
    "restore": BACKUP_MANAGE,
    "files": FILES_WRITE,
    "documents": FILES_WRITE,
    "workspace": FILES_WRITE,
    "workflows": DASHBOARD_READ,
    "tasks": DASHBOARD_READ,
    "catalog": DASHBOARD_READ,
    "helpdesk": HELPDESK_WRITE,
    "maintenance": MAINTENANCE_WRITE,
    "security": SECURITY_WRITE,
    "reports": REPORTS_GENERATE,
    "users": USERS_MANAGE,
    "settings": SETTINGS_MANAGE,
    "audit": AUDIT_READ,  # audit is read-only; no writes via UI
}

# Endpoint overrides (more specific than blueprint)
ENDPOINT_PERMISSIONS: dict[str, str] = {
    "users.assign_roles": ROLES_MANAGE,
    "assets.assign": ASSETS_ASSIGN,
    "helpdesk.assign": HELPDESK_ASSIGN,
    "helpdesk.create": HELPDESK_WRITE,
    "helpdesk.edit": HELPDESK_WRITE,
    "helpdesk.comment": HELPDESK_WRITE,
    "helpdesk.set_status": HELPDESK_WRITE,
    "helpdesk.add_link": HELPDESK_WRITE,
    "helpdesk.add_time": HELPDESK_WRITE,
    "helpdesk.knowledge_create": HELPDESK_ASSIGN,  # employees may read KB, not author it
    "helpdesk.knowledge_edit": HELPDESK_ASSIGN,
    "helpdesk.knowledge_delete": HELPDESK_ASSIGN,
    "helpdesk.knowledge_helpful": HELPDESK_READ,
    "helpdesk.export_csv": REPORTS_GENERATE,
    "ai.ask": DASHBOARD_READ,
    "ai.sessions": DASHBOARD_READ,
    "ai.session_messages": DASHBOARD_READ,
    "employee.connect": DASHBOARD_READ,
    "employee.connect_pair": DASHBOARD_READ,
    "profile.edit": DASHBOARD_READ,
    "profile.security": DASHBOARD_READ,
    "modules.profile_index": DASHBOARD_READ,
    "modules.profile_page": DASHBOARD_READ,
    "modules.notifications_index": DASHBOARD_READ,
    "modules.notifications_page": DASHBOARD_READ,
    "modules.search_index": DASHBOARD_READ,
    "modules.search_page": DASHBOARD_READ,
    "modules.knowledge_index": HELPDESK_READ,
    "modules.knowledge_page": HELPDESK_READ,
    "modules.alerts_index": MONITORING_READ,
    "modules.alerts_page": MONITORING_READ,
}


def session_permissions() -> set[str]:
    raw = session.get("permissions")
    if isinstance(raw, list):
        return set(raw)
    if isinstance(raw, set):
        return raw
    return set()


def is_super_admin_session() -> bool:
    user = session.get("user") or {}
    return bool(user.get("is_super_admin"))


def session_role_keys() -> list[str]:
    raw = session.get("role_keys")
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def is_employee_session() -> bool:
    """True when the user is municipal staff self-service (not IT ops roles)."""
    if is_super_admin_session():
        return False
    keys = set(session_role_keys())
    if not keys:
        return False
    it_ops = {"super_admin", "admin", "operator", "helpdesk", "agent"}
    if keys & it_ops:
        return False
    return bool(keys & {"employee", "viewer"})


def has_perm(*codes: str) -> bool:
    """True if session user has any of the given permission codes (or is super admin)."""
    if not session.get("user_id"):
        return False
    if is_super_admin_session():
        return True
    if not codes:
        return True
    perms = session_permissions()
    return any(code in perms for code in codes)


def sync_session_permissions() -> None:
    """Reload permissions from DB so role changes apply without re-login."""
    user_id = session.get("user_id")
    if not user_id:
        return
    try:
        from uitop.extensions import db
        from uitop.models.user import User

        user = db.session.get(User, user_id)
        if user is None or not user.is_active:
            return
        permissions = user.permission_codes()
        session["permissions"] = permissions
        roles = user.role_names()
        session["role_keys"] = roles
        current = session.get("user") or {}
        current["permissions"] = permissions
        current["is_super_admin"] = bool(user.is_super_admin)
        current["role_keys"] = roles
        if user.is_super_admin:
            current["role"] = "Super Admin"
        elif roles:
            from uitop.services.users_view import ROLE_LABELS

            current["role"] = ROLE_LABELS.get(roles[0], str(roles[0]).replace("_", " ").title())
        session["user"] = current
    except Exception:
        pass


def safe_home_endpoint() -> str:
    """First module the current user may open (never a locked page)."""
    if is_employee_session() and has_perm(DASHBOARD_READ):
        return "employee.index"
    candidates = (
        ("monitoring.index", MONITORING_READ),
        ("dashboard.index", DASHBOARD_READ),
        ("employee.index", DASHBOARD_READ),
        ("helpdesk.index", HELPDESK_READ),
        ("computers.index", COMPUTERS_READ),
        ("assets.index", ASSETS_READ),
        ("files.index", FILES_READ),
        ("profile.index", DASHBOARD_READ),
    )
    for endpoint, code in candidates:
        if has_perm(code):
            return endpoint
    return "profile.index"


def required_permission_for_request(endpoint: str | None, method: str) -> str | None:
    """Return permission code required for this UI request, or None if unrestricted."""
    if not endpoint or endpoint == "static" or endpoint.startswith("auth."):
        return None

    if endpoint in ENDPOINT_PERMISSIONS:
        return ENDPOINT_PERMISSIONS[endpoint]

    if endpoint.startswith("modules."):
        # Roles/departments scaffold redirects to users hub
        if "roles" in endpoint or "departments" in endpoint:
            return USERS_MANAGE
        return DASHBOARD_READ

    blueprint = endpoint.split(".", 1)[0]
    method = (method or "GET").upper()
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return BLUEPRINT_WRITE.get(blueprint) or BLUEPRINT_READ.get(blueprint)
    return BLUEPRINT_READ.get(blueprint)
