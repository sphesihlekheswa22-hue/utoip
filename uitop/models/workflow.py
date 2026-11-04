"""Workflow engine + cross-module work tasks."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


INSTANCE_STATUSES = (
    "open",
    "in_progress",
    "waiting",
    "completed",
    "rejected",
    "cancelled",
)

TASK_STATUSES = ("open", "in_progress", "done", "cancelled")
TASK_PRIORITIES = ("low", "medium", "high", "critical")

# Step action types in definition JSON
STEP_TYPES = ("submit", "review", "approve", "execute", "complete")


class WorkflowDefinition(db.Model):
    """Reusable process template (e.g. restore_request)."""

    __tablename__ = "workflow_definitions"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # [{key, label, type, role_keys?, permission?, creates_task?}]
    steps_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    instances = db.relationship("WorkflowInstance", back_populates="definition", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "steps": self.steps_json or [],
        }


class WorkflowInstance(db.Model):
    """One running workflow for a requester / resource."""

    __tablename__ = "workflow_instances"

    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(
        db.Integer, db.ForeignKey("workflow_definitions.id"), nullable=False, index=True
    )
    number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    current_step_key = db.Column(db.String(64), nullable=True, index=True)
    priority = db.Column(db.String(16), default="medium", nullable=False)

    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    resource_type = db.Column(db.String(64), nullable=True, index=True)
    resource_id = db.Column(db.Integer, nullable=True)
    resource_label = db.Column(db.String(255), nullable=True)
    payload_json = db.Column(db.JSON, nullable=True)

    due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    definition = db.relationship("WorkflowDefinition", back_populates="instances")
    requester = db.relationship("User", foreign_keys=[requester_user_id])
    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    events = db.relationship(
        "WorkflowEvent",
        back_populates="instance",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="WorkflowEvent.created_at.asc()",
    )
    tasks = db.relationship("WorkTask", back_populates="workflow_instance", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "status": self.status,
            "current_step_key": self.current_step_key,
            "priority": self.priority,
            "definition_key": self.definition.key if self.definition else None,
            "definition_name": self.definition.name if self.definition else None,
            "requester": self.requester.full_name if self.requester else None,
            "requester_user_id": self.requester_user_id,
            "assignee": self.assignee.full_name if self.assignee else None,
            "assignee_user_id": self.assignee_user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_label": self.resource_label,
            "payload": self.payload_json or {},
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WorkflowEvent(db.Model):
    __tablename__ = "workflow_events"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_key = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    note = db.Column(db.Text, nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    instance = db.relationship("WorkflowInstance", back_populates="events")
    actor = db.relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "step_key": self.step_key,
            "action": self.action,
            "note": self.note,
            "actor": self.actor.full_name if self.actor else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkTask(db.Model):
    """Assignable work item — often spawned by workflows or alerts."""

    __tablename__ = "work_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    priority = db.Column(db.String(16), default="medium", nullable=False, index=True)

    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    due_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    source_type = db.Column(db.String(64), nullable=True)  # workflow | alert | manual
    source_id = db.Column(db.Integer, nullable=True)
    workflow_instance_id = db.Column(
        db.Integer, db.ForeignKey("workflow_instances.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resource_type = db.Column(db.String(64), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    link_url = db.Column(db.String(512), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    workflow_instance = db.relationship("WorkflowInstance", back_populates="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee.full_name if self.assignee else None,
            "assignee_user_id": self.assignee_user_id,
            "created_by": self.created_by.full_name if self.created_by else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "source_type": self.source_type,
            "workflow_instance_id": self.workflow_instance_id,
            "workflow_number": self.workflow_instance.number if self.workflow_instance else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "link_url": self.link_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
