"""Helpdesk / ITSM ticket models."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


TICKET_STATUSES = ("open", "in_progress", "pending", "resolved", "closed")
TICKET_PRIORITIES = ("low", "medium", "high", "critical")
TICKET_TYPES = ("incident", "service_request", "problem")
TICKET_CATEGORIES = (
    "endpoint",
    "network",
    "printer",
    "account",
    "vpn",
    "email",
    "server",
    "software",
    "other",
)
OBJECT_LINK_TYPES = (
    "computer",
    "server",
    "network_device",
    "printer",
    "asset",
)
# Legacy single-link values still accepted on Ticket.linked_type
LINK_TYPES = (*OBJECT_LINK_TYPES, "none")

ACTIVITY_TYPES = (
    "created",
    "assigned",
    "status_changed",
    "priority_changed",
    "commented",
    "linked",
    "unlinked",
    "time_logged",
    "resolved",
    "closed",
    "reopened",
    "type_changed",
)


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    priority = db.Column(db.String(32), default="medium", nullable=False, index=True)
    category = db.Column(db.String(64), default="other", nullable=False)
    ticket_type = db.Column(db.String(32), default="incident", nullable=False, index=True)

    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    requester_name = db.Column(db.String(120), nullable=True)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    location = db.Column(db.String(255), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)
    # Legacy primary device link (kept for compatibility; mirrored into ticket_object_links)
    linked_type = db.Column(db.String(32), default="none", nullable=False)
    linked_id = db.Column(db.Integer, nullable=True)

    # Problem management: incidents/service requests can link to a parent problem
    problem_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=True, index=True)

    sla_due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    first_response_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    requester = db.relationship("User", foreign_keys=[requester_user_id])
    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    department = db.relationship("Department")
    asset = db.relationship("Asset")
    problem = db.relationship(
        "Ticket",
        remote_side=[id],
        foreign_keys=[problem_id],
        backref=db.backref("related_incidents", lazy="dynamic"),
    )
    comments = db.relationship(
        "TicketComment",
        back_populates="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )
    object_links = db.relationship(
        "TicketObjectLink",
        back_populates="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    time_logs = db.relationship(
        "TicketTimeLog",
        back_populates="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TicketTimeLog.started_at.desc()",
    )
    activities = db.relationship(
        "TicketActivity",
        back_populates="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TicketActivity.created_at.desc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "ticket_type": self.ticket_type,
            "requester_user_id": self.requester_user_id,
            "requester_name": self.requester_name,
            "assignee_user_id": self.assignee_user_id,
            "department_id": self.department_id,
            "location": self.location,
            "asset_id": self.asset_id,
            "linked_type": self.linked_type,
            "linked_id": self.linked_id,
            "problem_id": self.problem_id,
            "sla_due_at": self.sla_due_at.isoformat() if self.sla_due_at else None,
            "first_response_at": self.first_response_at.isoformat() if self.first_response_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = db.relationship("Ticket", back_populates="comments")
    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author_user_id": self.author_user_id,
            "author_name": self.author.full_name if self.author else "System",
            "body": self.body,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TicketObjectLink(db.Model):
    """Multi-object links: computer, printer, server, network, asset on one ticket."""

    __tablename__ = "ticket_object_links"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    link_type = db.Column(db.String(32), nullable=False, index=True)
    link_id = db.Column(db.Integer, nullable=False, index=True)
    label = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = db.relationship("Ticket", back_populates="object_links")

    __table_args__ = (
        db.UniqueConstraint("ticket_id", "link_type", "link_id", name="uq_ticket_object_link"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "type": self.link_type,
            "object_id": self.link_id,
            "label": self.label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TicketTimeLog(db.Model):
    __tablename__ = "ticket_time_logs"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    technician_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    minutes = db.Column(db.Integer, default=0, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = db.relationship("Ticket", back_populates="time_logs")
    technician = db.relationship("User", foreign_keys=[technician_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "technician_user_id": self.technician_user_id,
            "technician": self.technician.full_name if self.technician else "—",
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "minutes": self.minutes,
            "note": self.note,
        }


class TicketActivity(db.Model):
    __tablename__ = "ticket_activities"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(32), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = db.relationship("Ticket", back_populates="activities")
    actor = db.relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.activity_type,
            "message": self.message,
            "actor_user_id": self.actor_user_id,
            "actor": self.actor.full_name if self.actor else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


KB_CATEGORIES = (
    "endpoint",
    "network",
    "printer",
    "account",
    "vpn",
    "email",
    "server",
    "software",
    "general",
)


class KnowledgeArticle(db.Model):
    """Helpdesk knowledge base article."""

    __tablename__ = "knowledge_articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    summary = db.Column(db.String(512), nullable=True)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), default="general", nullable=False, index=True)
    tags = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, default=True, nullable=False, index=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    author = db.relationship("User", foreign_keys=[author_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "body": self.body,
            "category": self.category,
            "tags": self.tags,
            "is_published": self.is_published,
            "view_count": self.view_count,
            "helpful_count": self.helpful_count,
            "author_user_id": self.author_user_id,
            "author": self.author.full_name if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
