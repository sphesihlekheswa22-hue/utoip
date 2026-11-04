"""Agent telemetry models: performance, events, alerts."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class PerformanceSample(db.Model):
    __tablename__ = "performance_samples"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    collected_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    cpu_percent = db.Column(db.Float, nullable=True)
    memory_percent = db.Column(db.Float, nullable=True)
    memory_used_mb = db.Column(db.Float, nullable=True)
    memory_total_mb = db.Column(db.Float, nullable=True)
    disk_percent = db.Column(db.Float, nullable=True)
    disk_used_gb = db.Column(db.Float, nullable=True)
    disk_total_gb = db.Column(db.Float, nullable=True)
    network_bytes_sent = db.Column(db.BigInteger, nullable=True)
    network_bytes_recv = db.Column(db.BigInteger, nullable=True)
    process_count = db.Column(db.Integer, nullable=True)
    uptime_seconds = db.Column(db.Integer, nullable=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer", backref=db.backref("performance_samples", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "computer_id": self.computer_id,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "disk_percent": self.disk_percent,
            "disk_used_gb": self.disk_used_gb,
            "disk_total_gb": self.disk_total_gb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "process_count": self.process_count,
            "uptime_seconds": self.uptime_seconds,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentEvent(db.Model):
    __tablename__ = "agent_events"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(32), default="info", nullable=False, index=True)
    message = db.Column(db.String(512), nullable=False)
    source = db.Column(db.String(120), nullable=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer", backref=db.backref("agent_events", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "computer_id": self.computer_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentAlert(db.Model):
    __tablename__ = "agent_alerts"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    alert_code = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(32), default="warning", nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.String(1024), nullable=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    computer = db.relationship("Computer", backref=db.backref("agent_alerts", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "computer_id": self.computer_id,
            "alert_code": self.alert_code,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentCommand(db.Model):
    """Queued remote action for an enrolled agent to execute."""

    __tablename__ = "agent_commands"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True, index=True)
    command = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(32), default="pending", nullable=False, index=True)
    params = db.Column(db.JSON, nullable=True)
    result = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    computer = db.relationship("Computer", backref=db.backref("agent_commands", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "computer_id": self.computer_id,
            "command": self.command,
            "status": self.status,
            "params": self.params or {},
            "result": self.result,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
