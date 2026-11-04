"""Security posture & compliance — not a SIEM or AV replacement."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


SEVERITIES = ("critical", "high", "medium", "low", "info")
FINDING_STATUSES = ("open", "investigating", "mitigated", "closed", "false_positive")
INCIDENT_STATUSES = ("open", "investigating", "contained", "resolved", "closed")
POLICY_KEYS = (
    "password_min_length",
    "bitlocker_required",
    "firewall_required",
    "antivirus_required",
    "usb_storage_blocked",
    "windows_update_required",
)


class DeviceSecurityPosture(db.Model):
    """Per-device security posture reported by agent (or demo seed)."""

    __tablename__ = "device_security_postures"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False, unique=True, index=True)
    antivirus_name = db.Column(db.String(120), nullable=True)
    antivirus_enabled = db.Column(db.Boolean, default=True, nullable=False)
    antivirus_definitions_ok = db.Column(db.Boolean, default=True, nullable=False)
    last_scan_at = db.Column(db.DateTime(timezone=True), nullable=True)
    firewall_enabled = db.Column(db.Boolean, default=True, nullable=False)
    bitlocker_enabled = db.Column(db.Boolean, default=False, nullable=False)
    windows_updated = db.Column(db.Boolean, default=True, nullable=False)
    pending_updates = db.Column(db.Integer, default=0, nullable=False)
    usb_storage_allowed = db.Column(db.Boolean, default=True, nullable=False)
    compliance_score = db.Column(db.Integer, default=100, nullable=False)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    last_reported_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    computer = db.relationship("Computer", backref=db.backref("security_posture", uselist=False))

    @property
    def is_protected(self) -> bool:
        return bool(self.antivirus_enabled and self.firewall_enabled)

    def to_dict(self):
        return {
            "id": self.id,
            "computer_id": self.computer_id,
            "antivirus_name": self.antivirus_name,
            "antivirus_enabled": self.antivirus_enabled,
            "antivirus_definitions_ok": self.antivirus_definitions_ok,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "firewall_enabled": self.firewall_enabled,
            "bitlocker_enabled": self.bitlocker_enabled,
            "windows_updated": self.windows_updated,
            "pending_updates": self.pending_updates,
            "usb_storage_allowed": self.usb_storage_allowed,
            "compliance_score": self.compliance_score,
            "risk_score": self.risk_score,
            "is_protected": self.is_protected,
            "last_reported_at": self.last_reported_at.isoformat() if self.last_reported_at else None,
        }


class SecurityThreat(db.Model):
    __tablename__ = "security_threats"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    threat_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(32), default="high", nullable=False, index=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    hostname = db.Column(db.String(255), nullable=True)
    detected_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer")
    ticket = db.relationship("Ticket")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "threat_type": self.threat_type,
            "severity": self.severity,
            "status": self.status,
            "computer_id": self.computer_id,
            "hostname": self.hostname,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "ticket_id": self.ticket_id,
        }


class SecurityVulnerability(db.Model):
    __tablename__ = "security_vulnerabilities"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=False, index=True)  # update, software, config, cve
    severity = db.Column(db.String(32), default="medium", nullable=False, index=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    hostname = db.Column(db.String(255), nullable=True)
    cve_id = db.Column(db.String(64), nullable=True)
    detected_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "computer_id": self.computer_id,
            "hostname": self.hostname,
            "cve_id": self.cve_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }


class SecurityIncident(db.Model):
    __tablename__ = "security_incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    incident_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(32), default="high", nullable=False, index=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    hostname = db.Column(db.String(255), nullable=True)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=True)
    detected_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    computer = db.relationship("Computer")
    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    ticket = db.relationship("Ticket")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_number": self.incident_number,
            "title": self.title,
            "description": self.description,
            "incident_type": self.incident_type,
            "severity": self.severity,
            "status": self.status,
            "computer_id": self.computer_id,
            "hostname": self.hostname,
            "assignee_user_id": self.assignee_user_id,
            "ticket_id": self.ticket_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class SecurityPolicy(db.Model):
    __tablename__ = "security_policies"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    value = db.Column(db.String(255), nullable=False)
    is_enforced = db.Column(db.Boolean, default=True, nullable=False)
    category = db.Column(db.String(64), default="general", nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "is_enforced": self.is_enforced,
            "category": self.category,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SecurityUserActivity(db.Model):
    """Failed logins, lockouts, password resets, new admin accounts."""

    __tablename__ = "security_user_activities"

    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(64), nullable=False, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True)
    hostname = db.Column(db.String(255), nullable=True)
    count = db.Column(db.Integer, default=1, nullable=False)
    severity = db.Column(db.String(32), default="medium", nullable=False)
    message = db.Column(db.String(512), nullable=True)
    occurred_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])
    computer = db.relationship("Computer")

    def to_dict(self):
        return {
            "id": self.id,
            "activity_type": self.activity_type,
            "username": self.username,
            "user_id": self.user_id,
            "computer_id": self.computer_id,
            "hostname": self.hostname,
            "count": self.count,
            "severity": self.severity,
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }


class SecurityAuditEvent(db.Model):
    """Security-related audit trail (subset of full platform audit)."""

    __tablename__ = "security_audit_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    message = db.Column(db.String(512), nullable=False)
    severity = db.Column(db.String(32), default="info", nullable=False)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True)
    hostname = db.Column(db.String(255), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    occurred_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer")
    actor = db.relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "message": self.message,
            "severity": self.severity,
            "computer_id": self.computer_id,
            "hostname": self.hostname,
            "actor_user_id": self.actor_user_id,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
