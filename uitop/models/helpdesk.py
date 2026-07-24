"""Helpdesk ticket models."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


TICKET_STATUSES = ("open", "in_progress", "pending", "resolved", "closed")
TICKET_PRIORITIES = ("low", "medium", "high", "critical")
TICKET_CATEGORIES = (
    "endpoint",
    "network",
    "printer",
    "account",
    "vpn",
    "email",
    "server",
    "other",
)
LINK_TYPES = ("computer", "server", "network_device", "printer", "none")


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)
    priority = db.Column(db.String(32), default="medium", nullable=False, index=True)
    category = db.Column(db.String(64), default="other", nullable=False)

    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    requester_name = db.Column(db.String(120), nullable=True)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    location = db.Column(db.String(255), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)
    linked_type = db.Column(db.String(32), default="none", nullable=False)
    linked_id = db.Column(db.Integer, nullable=True)

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
    comments = db.relationship(
        "TicketComment",
        back_populates="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
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
            "requester_user_id": self.requester_user_id,
            "requester_name": self.requester_name,
            "assignee_user_id": self.assignee_user_id,
            "department_id": self.department_id,
            "location": self.location,
            "asset_id": self.asset_id,
            "linked_type": self.linked_type,
            "linked_id": self.linked_id,
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
