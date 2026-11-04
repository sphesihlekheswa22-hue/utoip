"""Copilot conversation models."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class CopilotSession(db.Model):
    __tablename__ = "copilot_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("copilot_sessions", lazy="dynamic"))
    messages = db.relationship("CopilotMessage", backref="session", lazy="dynamic",
                               order_by="CopilotMessage.created_at",
                               cascade="all, delete-orphan")

    def history(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


class CopilotMessage(db.Model):
    __tablename__ = "copilot_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("copilot_sessions.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(16), nullable=False)   # "user" | "assistant"
    content = db.Column(db.Text, nullable=False)
    context_snapshot = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
