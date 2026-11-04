"""SQLAlchemy models."""
from uitop.models.agent_telemetry import AgentAlert, AgentCommand, AgentEvent, PerformanceSample
from uitop.models.api_client import ApiClient
from uitop.models.assets import Asset, AssetAssignment, AssetCategory, AssetRequest, AssetVendor
from uitop.models.audit import AuditLog
from uitop.models.settings import SystemSetting
from uitop.models.auth import AgentEnrollmentToken, RefreshToken
from uitop.models.department import Department
from uitop.models.files import (
    FileActivity,
    FileLink,
    FilePermission,
    FileTag,
    FileVersion,
    DocumentApproval,
    RepoFile,
)
from uitop.models.helpdesk import (
    Ticket,
    TicketActivity,
    TicketComment,
    TicketObjectLink,
    TicketTimeLog,
    KnowledgeArticle,
)
from uitop.models.notifications import AppNotification
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.snmp import SnmpProfile
from uitop.models.maintenance import (
    MaintenanceActivity,
    MaintenanceChecklistItem,
    MaintenancePart,
    MaintenancePlan,
    MaintenanceWorkOrder,
)
from uitop.models.security import (
    DeviceSecurityPosture,
    SecurityAuditEvent,
    SecurityIncident,
    SecurityPolicy,
    SecurityThreat,
    SecurityUserActivity,
    SecurityVulnerability,
)
from uitop.models.copilot import CopilotMessage, CopilotSession
from uitop.models.workflow import WorkflowDefinition, WorkflowEvent, WorkflowInstance, WorkTask
from uitop.models.site_connector import SiteConnector
from uitop.models.role import Permission, Role, role_permissions, user_roles
from uitop.models.user import User

__all__ = [
    "User",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
    "Department",
    "RefreshToken",
    "ApiClient",
    "AuditLog",
    "SystemSetting",
    "Computer",
    "Server",
    "NetworkDevice",
    "Printer",
    "SnmpProfile",
    "AgentEnrollmentToken",
    "PerformanceSample",
    "AgentEvent",
    "AgentAlert",
    "AgentCommand",
    "Asset",
    "AssetCategory",
    "AssetVendor",
    "AssetAssignment",
    "AssetRequest",
    "Ticket",
    "TicketComment",
    "TicketObjectLink",
    "TicketTimeLog",
    "TicketActivity",
    "KnowledgeArticle",
    "AppNotification",
    "RepoFile",
    "FileVersion",
    "FileLink",
    "FileTag",
    "FilePermission",
    "FileActivity",
    "DocumentApproval",
    "MaintenanceWorkOrder",
    "MaintenanceChecklistItem",
    "MaintenancePart",
    "MaintenanceActivity",
    "MaintenancePlan",
    "DeviceSecurityPosture",
    "SecurityThreat",
    "SecurityVulnerability",
    "SecurityIncident",
    "SecurityPolicy",
    "SecurityUserActivity",
    "SecurityAuditEvent",
    "CopilotSession",
    "CopilotMessage",
    "WorkflowDefinition",
    "WorkflowInstance",
    "WorkflowEvent",
    "WorkTask",
    "SiteConnector",
]
