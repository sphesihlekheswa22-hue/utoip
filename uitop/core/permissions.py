"""Permission codes used across RBAC."""

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

# Helpdesk
HELPDESK_READ = "helpdesk:read"
HELPDESK_WRITE = "helpdesk:write"
HELPDESK_ASSIGN = "helpdesk:assign"

# Enterprise IT file repository
FILES_READ = "files:read"
FILES_WRITE = "files:write"
FILES_MANAGE = "files:manage"

# Administration
USERS_MANAGE = "users:manage"
ROLES_MANAGE = "roles:manage"
DEPARTMENTS_MANAGE = "departments:manage"
AUDIT_READ = "audit:read"

# Agents
AGENTS_REGISTER = "agents:register"
AGENTS_HEARTBEAT = "agents:heartbeat"
AGENTS_INVENTORY = "agents:inventory"
AGENTS_PERFORMANCE = "agents:performance"
AGENTS_EVENTS = "agents:events"
AGENTS_ALERTS = "agents:alerts"
AGENTS_MANAGE = "agents:manage"

DEFAULT_AGENT_SCOPES = [
    AGENTS_HEARTBEAT,
    AGENTS_INVENTORY,
    AGENTS_PERFORMANCE,
    AGENTS_EVENTS,
    AGENTS_ALERTS,
    COMPUTERS_WRITE,
]

ALL_PERMISSIONS = [
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
    (HELPDESK_READ, "View helpdesk tickets"),
    (HELPDESK_WRITE, "Create and update tickets"),
    (HELPDESK_ASSIGN, "Assign tickets"),
    (FILES_READ, "View IT repository files"),
    (FILES_WRITE, "Upload and link repository files"),
    (FILES_MANAGE, "Manage file permissions and versions"),
    (USERS_MANAGE, "Manage users"),
    (ROLES_MANAGE, "Manage roles"),
    (DEPARTMENTS_MANAGE, "Manage departments"),
    (AUDIT_READ, "View audit logs"),
    (AGENTS_REGISTER, "Register agents"),
    (AGENTS_HEARTBEAT, "Agent heartbeat"),
    (AGENTS_INVENTORY, "Submit agent inventory"),
    (AGENTS_PERFORMANCE, "Submit performance samples"),
    (AGENTS_EVENTS, "Submit agent events"),
    (AGENTS_ALERTS, "Submit agent alerts"),
    (AGENTS_MANAGE, "Manage agent enrollment"),
]

ROLE_PERMISSIONS = {
    "super_admin": [code for code, _ in ALL_PERMISSIONS],
    "admin": [
        COMPUTERS_READ,
        COMPUTERS_WRITE,
        SERVERS_READ,
        SERVERS_WRITE,
        NETWORK_READ,
        NETWORK_WRITE,
        PRINTERS_READ,
        PRINTERS_WRITE,
        ASSETS_READ,
        ASSETS_WRITE,
        ASSETS_ASSIGN,
        ASSETS_DISPOSE,
        HELPDESK_READ,
        HELPDESK_WRITE,
        HELPDESK_ASSIGN,
        FILES_READ,
        FILES_WRITE,
        FILES_MANAGE,
        USERS_MANAGE,
        DEPARTMENTS_MANAGE,
        AUDIT_READ,
        AGENTS_MANAGE,
        AGENTS_REGISTER,
    ],
    "operator": [
        COMPUTERS_READ,
        COMPUTERS_WRITE,
        SERVERS_READ,
        SERVERS_WRITE,
        NETWORK_READ,
        NETWORK_WRITE,
        PRINTERS_READ,
        PRINTERS_WRITE,
        ASSETS_READ,
        ASSETS_WRITE,
        ASSETS_ASSIGN,
        HELPDESK_READ,
        HELPDESK_WRITE,
        HELPDESK_ASSIGN,
        FILES_READ,
        FILES_WRITE,
        AGENTS_MANAGE,
        AGENTS_REGISTER,
    ],
    "helpdesk": [
        COMPUTERS_READ,
        SERVERS_READ,
        NETWORK_READ,
        PRINTERS_READ,
        ASSETS_READ,
        ASSETS_ASSIGN,
        HELPDESK_READ,
        HELPDESK_WRITE,
        HELPDESK_ASSIGN,
        FILES_READ,
        FILES_WRITE,
    ],
    "viewer": [
        COMPUTERS_READ,
        SERVERS_READ,
        NETWORK_READ,
        PRINTERS_READ,
        ASSETS_READ,
        HELPDESK_READ,
        FILES_READ,
        AUDIT_READ,
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
    "super_admin": "Full platform access",
    "admin": "Administrative access excluding role catalog edits",
    "operator": "Day-to-day inventory and agent operations",
    "helpdesk": "Support staff — tickets plus read inventory",
    "viewer": "Read-only access including audit",
    "agent": "Machine identity for enrolled agents",
}
