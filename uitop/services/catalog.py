"""Employee service request catalog — ServiceNow-style offerings."""
from __future__ import annotations

# Catalog items map to workflow definition keys.
# Icons use Font Awesome class names (without "fa-").

CATALOG_ITEMS: list[dict] = [
    {
        "key": "new_laptop",
        "name": "New Laptop",
        "summary": "Request a new laptop for municipal work.",
        "description": "Submit a justified request for a laptop. Helpdesk reviews; IT fulfills after approval.",
        "category": "Hardware",
        "icon": "laptop",
        "workflow_key": "service_request",
        "default_priority": "medium",
        "fields": [
            {"name": "justification", "label": "Business justification", "type": "textarea", "required": True},
            {"name": "preferred_model", "label": "Preferred model (optional)", "type": "text", "required": False},
        ],
    },
    {
        "key": "password_reset",
        "name": "Password Reset",
        "summary": "Reset domain / email password with IT assistance.",
        "description": "Use when self-service reset is unavailable. Helpdesk will verify identity and reset.",
        "category": "Account",
        "icon": "key",
        "workflow_key": "service_request",
        "default_priority": "high",
        "fields": [
            {"name": "account", "label": "Account / email", "type": "text", "required": True},
            {"name": "details", "label": "What happened?", "type": "textarea", "required": False},
        ],
    },
    {
        "key": "office_install",
        "name": "Microsoft Office Installation",
        "summary": "Install or repair Office on your PC.",
        "description": "Request Office installation or repair. May require software approval.",
        "category": "Software",
        "icon": "file-word",
        "workflow_key": "software_install",
        "default_priority": "medium",
        "fields": [
            {"name": "device", "label": "Computer hostname", "type": "text", "required": True},
            {"name": "details", "label": "Notes", "type": "textarea", "required": False},
        ],
    },
    {
        "key": "software_install",
        "name": "Software Installation",
        "summary": "Request approved software on your device.",
        "description": "Helpdesk reviews; IT Admin approves licensed software before install.",
        "category": "Software",
        "icon": "cube",
        "workflow_key": "software_install",
        "default_priority": "medium",
        "fields": [
            {"name": "software_name", "label": "Software name", "type": "text", "required": True},
            {"name": "device", "label": "Computer hostname", "type": "text", "required": True},
            {"name": "justification", "label": "Why do you need it?", "type": "textarea", "required": True},
        ],
    },
    {
        "key": "printer_access",
        "name": "Printer Access",
        "summary": "Connect to an office printer.",
        "description": "Request access to a departmental or shared printer.",
        "category": "Hardware",
        "icon": "print",
        "workflow_key": "service_request",
        "default_priority": "medium",
        "fields": [
            {"name": "printer_name", "label": "Printer name / location", "type": "text", "required": True},
            {"name": "details", "label": "Notes", "type": "textarea", "required": False},
        ],
    },
    {
        "key": "vpn_access",
        "name": "VPN Access",
        "summary": "Remote access to municipal systems.",
        "description": "Request VPN for remote work. Helpdesk verifies eligibility and configures access.",
        "category": "Access",
        "icon": "shield-halved",
        "workflow_key": "service_request",
        "default_priority": "high",
        "fields": [
            {"name": "justification", "label": "Why do you need VPN?", "type": "textarea", "required": True},
            {"name": "manager", "label": "Manager name", "type": "text", "required": False},
        ],
    },
    {
        "key": "email_account",
        "name": "Email Account",
        "summary": "New municipal email mailbox.",
        "description": "Request a new @umzinyathi.gov.za mailbox or shared mailbox.",
        "category": "Account",
        "icon": "envelope",
        "workflow_key": "service_request",
        "default_priority": "medium",
        "fields": [
            {"name": "mailbox_type", "label": "Type (user / shared)", "type": "text", "required": True},
            {"name": "display_name", "label": "Display name", "type": "text", "required": True},
            {"name": "details", "label": "Notes", "type": "textarea", "required": False},
        ],
    },
    {
        "key": "shared_folder",
        "name": "Shared Folder Access",
        "summary": "Access to a file share or department folder.",
        "description": "Request read or write access to a shared folder. Owner/IT must approve.",
        "category": "Access",
        "icon": "folder-open",
        "workflow_key": "service_request",
        "default_priority": "medium",
        "fields": [
            {"name": "folder_path", "label": "Folder / share name", "type": "text", "required": True},
            {"name": "access_level", "label": "Access needed (read / write)", "type": "text", "required": True},
            {"name": "justification", "label": "Justification", "type": "textarea", "required": True},
        ],
    },
    {
        "key": "backup_restore",
        "name": "Backup Restore",
        "summary": "Restore files or a PC from backup.",
        "description": "Opens the restore workflow — IT reviews, then executes the restore.",
        "category": "Backup",
        "icon": "rotate-left",
        "workflow_key": "restore_request",
        "default_priority": "high",
        "fields": [],
        "redirect": "workflows.restore_request",
    },
]


def list_catalog(*, category: str | None = None, q: str | None = None) -> list[dict]:
    rows = list(CATALOG_ITEMS)
    if category:
        rows = [r for r in rows if r.get("category") == category]
    if q:
        term = q.strip().lower()
        rows = [
            r
            for r in rows
            if term in (r.get("name") or "").lower()
            or term in (r.get("summary") or "").lower()
            or term in (r.get("category") or "").lower()
        ]
    return rows


def catalog_categories() -> list[str]:
    seen = []
    for item in CATALOG_ITEMS:
        c = item.get("category") or "Other"
        if c not in seen:
            seen.append(c)
    return seen


def get_catalog_item(key: str) -> dict | None:
    key = (key or "").strip()
    for item in CATALOG_ITEMS:
        if item.get("key") == key:
            return item
    return None
