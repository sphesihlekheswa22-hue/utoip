"""Permission codes used across RBAC."""

# Overview
DASHBOARD_READ = "dashboard:read"
MONITORING_READ = "monitoring:read"

# Inventory
COMPUTERS_READ = "computers:read"
COMPUTERS_WRITE = "computers:write"
SERVERS_READ = "servers:read"
SERVERS_WRITE = "servers:write"
NETWORK_READ = "network:read"
NETWORK_WRITE = "network:write"
PRINTERS_READ = "printers:read"
PRINTERS_WRITE = "printers:write"

# Assets (lifecycle / ownership)
ASSETS_READ = "assets:read"
ASSETS_WRITE = "assets:write"
ASSETS_ASSIGN = "assets:assign"
ASSETS_DISPOSE = "assets:dispose"

# Software estate
SOFTWARE_READ = "software:read"
SOFTWARE_WRITE = "software:write"
LICENSES_READ = "licenses:read"
LICENSES_WRITE = "licenses:write"
VENDORS_READ = "vendors:read"
VENDORS_WRITE = "vendors:write"

# Helpdesk
HELPDESK_READ = "helpdesk:read"
HELPDESK_WRITE = "helpdesk:write"
HELPDESK_ASSIGN = "helpdesk:assign"

# Enterprise IT file repository
FILES_READ = "files:read"
FILES_WRITE = "files:write"
FILES_MANAGE = "files:manage"

# Operations
MAINTENANCE_READ = "maintenance:read"
MAINTENANCE_WRITE = "maintenance:write"
CALENDAR_READ = "calendar:read"
SECURITY_READ = "security:read"
SECURITY_WRITE = "security:write"
BACKUP_READ = "backup:read"
BACKUP_MANAGE = "backup:manage"

# Insights
ANALYSIS_READ = "analysis:read"
REPORTS_READ = "reports:read"
REPORTS_GENERATE = "reports:generate"

# Administration
USERS_MANAGE = "users:manage"
ROLES_MANAGE = "roles:manage"
DEPARTMENTS_MANAGE = "departments:manage"
AUDIT_READ = "audit:read"
SETTINGS_MANAGE = "settings:manage"

# Agents
AGENTS_REGISTER = "agents:register"
AGENTS_HEARTBEAT = "agents:heartbeat"
AGENTS_INVENTORY = "agents:inventory"
AGENTS_PERFORMANCE = "agents:performance"
AGENTS_EVENTS = "agents:events"
AGENTS_ALERTS = "agents:alerts"
AGENTS_MANAGE = "agents:manage"

# Site connectors (LAN scanners pushing discovery to cloud)
CONNECTORS_HEARTBEAT = "connectors:heartbeat"
CONNECTORS_NETWORK_INGEST = "connectors:network_ingest"
CONNECTORS_PRINTER_INGEST = "connectors:printer_ingest"
CONNECTORS_MANAGE = "connectors:manage"

DEFAULT_AGENT_SCOPES = [
    AGENTS_HEARTBEAT,
    AGENTS_INVENTORY,
    AGENTS_PERFORMANCE,
    AGENTS_EVENTS,
    AGENTS_ALERTS,
    COMPUTERS_WRITE,
]

DEFAULT_CONNECTOR_SCOPES = [
    CONNECTORS_HEARTBEAT,
    CONNECTORS_NETWORK_INGEST,
    CONNECTORS_PRINTER_INGEST,
    NETWORK_WRITE,
    PRINTERS_WRITE,
    COMPUTERS_WRITE,
    SERVERS_WRITE,
]

ALL_PERMISSIONS = [
    (DASHBOARD_READ, "View dashboard"),
    (MONITORING_READ, "View monitoring and alerts"),
    (COMPUTERS_READ, "View computers"),
    (COMPUTERS_WRITE, "Manage computers"),
    (SERVERS_READ, "View servers"),
    (SERVERS_WRITE, "Manage servers"),
    (NETWORK_READ, "View network devices"),
    (NETWORK_WRITE, "Manage network devices"),
    (PRINTERS_READ, "View printers"),
    (PRINTERS_WRITE, "Manage printers"),
    (ASSETS_READ, "View assets"),
    (ASSETS_WRITE, "Create and update assets"),
    (ASSETS_ASSIGN, "Assign and transfer assets"),
    (ASSETS_DISPOSE, "Dispose assets"),
    (SOFTWARE_READ, "View software catalog"),
    (SOFTWARE_WRITE, "Manage software"),
    (LICENSES_READ, "View licenses"),
    (LICENSES_WRITE, "Manage licenses"),
    (VENDORS_READ, "View vendors"),
    (VENDORS_WRITE, "Manage vendors"),
    (HELPDESK_READ, "View helpdesk tickets"),
    (HELPDESK_WRITE, "Create and update tickets"),
    (HELPDESK_ASSIGN, "Assign tickets"),
    (FILES_READ, "View IT repository files"),
    (FILES_WRITE, "Upload and link repository files"),
    (FILES_MANAGE, "Manage file permissions and versions"),
    (MAINTENANCE_READ, "View maintenance"),
    (MAINTENANCE_WRITE, "Manage work orders"),
    (CALENDAR_READ, "View operations calendar"),
    (SECURITY_READ, "View security posture"),
    (SECURITY_WRITE, "Manage security records"),
    (BACKUP_READ, "View backup status"),
    (BACKUP_MANAGE, "Manage backup jobs"),
    (ANALYSIS_READ, "View analysis insights"),
    (REPORTS_READ, "View reports"),
    (REPORTS_GENERATE, "Generate and export reports"),
    (USERS_MANAGE, "Manage users"),
    (ROLES_MANAGE, "Manage roles"),
    (DEPARTMENTS_MANAGE, "Manage departments"),
    (AUDIT_READ, "View audit logs"),
    (SETTINGS_MANAGE, "Manage platform settings"),
    (AGENTS_REGISTER, "Register agents"),
    (AGENTS_HEARTBEAT, "Agent heartbeat"),
    (AGENTS_INVENTORY, "Submit agent inventory"),
    (AGENTS_PERFORMANCE, "Submit performance samples"),
    (AGENTS_EVENTS, "Submit agent events"),
    (AGENTS_ALERTS, "Submit agent alerts"),
    (AGENTS_MANAGE, "Manage agent enrollment"),
    (CONNECTORS_HEARTBEAT, "Site connector heartbeat"),
    (CONNECTORS_NETWORK_INGEST, "Ingest LAN network scan results"),
    (CONNECTORS_PRINTER_INGEST, "Ingest printer discovery / SNMP"),
    (CONNECTORS_MANAGE, "Manage site connectors"),
]

# Shared packs
_INFRA_READ = [COMPUTERS_READ, SERVERS_READ, NETWORK_READ, PRINTERS_READ, MONITORING_READ]
_INFRA_WRITE = [COMPUTERS_WRITE, SERVERS_WRITE, NETWORK_WRITE, PRINTERS_WRITE]
_ASSET_PACK_READ = [ASSETS_READ, SOFTWARE_READ, LICENSES_READ, VENDORS_READ]
_OPS_READ = [MAINTENANCE_READ, CALENDAR_READ, SECURITY_READ, BACKUP_READ]

ROLE_PERMISSIONS = {
    # 1. Super Administrator — owns the entire platform
    "super_admin": [code for code, _ in ALL_PERMISSIONS],

    # 2. IT Administrator — infrastructure & operations (not platform security/roles/settings)
    "admin": [
        DASHBOARD_READ,
        *_INFRA_READ,
        *_INFRA_WRITE,
        *_ASSET_PACK_READ,
        ASSETS_WRITE,
        ASSETS_ASSIGN,
        SOFTWARE_WRITE,
        LICENSES_WRITE,
        VENDORS_WRITE,
        HELPDESK_READ,
        HELPDESK_WRITE,
        HELPDESK_ASSIGN,
        FILES_READ,
        FILES_WRITE,
        FILES_MANAGE,
        *_OPS_READ,
        MAINTENANCE_WRITE,
        SECURITY_READ,
        BACKUP_MANAGE,
        ANALYSIS_READ,
        REPORTS_READ,
        REPORTS_GENERATE,
        AUDIT_READ,
        AGENTS_MANAGE,
        AGENTS_REGISTER,
        CONNECTORS_MANAGE,
    ],

    # 3. Operator — day-to-day ops (no user/role/settings; no asset dispose)
    "operator": [
        DASHBOARD_READ,
        *_INFRA_READ,
        *_ASSET_PACK_READ,
        ASSETS_WRITE,
        ASSETS_ASSIGN,
        HELPDESK_READ,
        HELPDESK_WRITE,
        FILES_READ,
        FILES_WRITE,
        *_OPS_READ,
        MAINTENANCE_WRITE,
        BACKUP_MANAGE,
        ANALYSIS_READ,
        REPORTS_READ,
        REPORTS_GENERATE,
        AGENTS_REGISTER,
        CONNECTORS_MANAGE,
    ],

    # 4. Helpdesk — tickets & support only (no backups manage, no asset manage, no network scan/write)
    "helpdesk": [
        DASHBOARD_READ,
        MONITORING_READ,
        COMPUTERS_READ,
        SERVERS_READ,
        PRINTERS_READ,
        ASSETS_READ,
        SOFTWARE_READ,
        HELPDESK_READ,
        HELPDESK_WRITE,
        HELPDESK_ASSIGN,
        FILES_READ,
        FILES_WRITE,
        CALENDAR_READ,
        MAINTENANCE_READ,
        REPORTS_READ,
        REPORTS_GENERATE,
    ],

    # 5. Employee — municipal staff self-service (not IT department)
    "employee": [
        DASHBOARD_READ,
        COMPUTERS_READ,
        PRINTERS_READ,
        ASSETS_READ,
        HELPDESK_READ,
        HELPDESK_WRITE,
        FILES_READ,
        FILES_WRITE,
        BACKUP_READ,
    ],

    "agent": [
        AGENTS_REGISTER,
        AGENTS_HEARTBEAT,
        AGENTS_INVENTORY,
        AGENTS_PERFORMANCE,
        AGENTS_EVENTS,
        AGENTS_ALERTS,
        COMPUTERS_WRITE,
        SERVERS_WRITE,
    ],
}

ROLE_DESCRIPTIONS = {
    "super_admin": "Owns and manages the entire UITOP platform",
    "admin": "IT Administrator — infrastructure and operations (no core settings or role design)",
    "operator": "Day-to-day operational tasks — backups, assets, maintenance, reports",
    "helpdesk": "Supports employees — tickets, KB, AI troubleshooting (no backup restore or asset management)",
    "employee": "Municipal staff self-service — request IT support, view own devices and tickets",
    "agent": "Machine identity for enrolled agents",
}
