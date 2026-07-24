"""SQLAlchemy models."""
from uitop.models.agent_telemetry import AgentAlert, AgentEvent, PerformanceSample
from uitop.models.api_client import ApiClient
from uitop.models.assets import Asset, AssetAssignment, AssetCategory, AssetRequest, AssetVendor
from uitop.models.audit import AuditLog
from uitop.models.auth import AgentEnrollmentToken, RefreshToken
from uitop.models.department import Department
from uitop.models.files import (
    FileActivity,
    FileLink,
    FilePermission,
    FileTag,
    FileVersion,
    RepoFile,
)
from uitop.models.helpdesk import Ticket, TicketComment
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
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
    "Computer",
    "Server",
    "NetworkDevice",
    "Printer",
    "AgentEnrollmentToken",
    "PerformanceSample",
    "AgentEvent",
    "AgentAlert",
    "Asset",
    "AssetCategory",
    "AssetVendor",
    "AssetAssignment",
    "AssetRequest",
    "Ticket",
    "TicketComment",
    "RepoFile",
    "FileVersion",
    "FileLink",
    "FileTag",
    "FilePermission",
    "FileActivity",
]
