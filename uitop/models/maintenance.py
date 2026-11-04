"""Preventive & corrective maintenance — work-order centered."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


WO_STATUSES = ("scheduled", "in_progress", "on_hold", "completed", "cancelled")
WO_TYPES = ("preventive", "corrective", "emergency")
WO_PRIORITIES = ("low", "medium", "high", "critical")
ASSET_LINK_TYPES = ("computer", "server", "network_device", "printer", "asset")
PLAN_FREQUENCIES = ("weekly", "monthly", "quarterly", "yearly", "custom_days")


class MaintenanceWorkOrder(db.Model):
    __tablename__ = "maintenance_work_orders"

    id = db.Column(db.Integer, primary_key=True)
    work_order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    maintenance_type = db.Column(db.String(32), default="preventive", nullable=False, index=True)
    status = db.Column(db.String(32), default="scheduled", nullable=False, index=True)
    priority = db.Column(db.String(32), default="medium", nullable=False, index=True)

    # Linked infrastructure / asset
    linked_type = db.Column(db.String(32), default="asset", nullable=False, index=True)
    linked_id = db.Column(db.Integer, nullable=True, index=True)
    linked_label = db.Column(db.String(255), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)

    technician_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("asset_vendors.id"), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("maintenance_plans.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    location = db.Column(db.String(255), nullable=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    due_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    labour_cost = db.Column(db.Float, default=0.0, nullable=False)
    parts_cost = db.Column(db.Float, default=0.0, nullable=False)
    travel_cost = db.Column(db.Float, default=0.0, nullable=False)
    other_cost = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    technician = db.relationship("User", foreign_keys=[technician_user_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    vendor = db.relationship("AssetVendor")
    asset = db.relationship("Asset")
    ticket = db.relationship("Ticket")
    plan = db.relationship("MaintenancePlan", back_populates="work_orders")
    checklist_items = db.relationship(
        "MaintenanceChecklistItem",
        back_populates="work_order",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="MaintenanceChecklistItem.sort_order",
    )
    parts = db.relationship(
        "MaintenancePart",
        back_populates="work_order",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    activities = db.relationship(
        "MaintenanceActivity",
        back_populates="work_order",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="MaintenanceActivity.created_at.desc()",
    )

    @property
    def total_cost(self) -> float:
        return float(self.labour_cost or 0) + float(self.parts_cost or 0) + float(self.travel_cost or 0) + float(
            self.other_cost or 0
        )

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_number": self.work_order_number,
            "title": self.title,
            "description": self.description,
            "maintenance_type": self.maintenance_type,
            "status": self.status,
            "priority": self.priority,
            "linked_type": self.linked_type,
            "linked_id": self.linked_id,
            "linked_label": self.linked_label,
            "asset_id": self.asset_id,
            "technician_user_id": self.technician_user_id,
            "vendor_id": self.vendor_id,
            "ticket_id": self.ticket_id,
            "plan_id": self.plan_id,
            "location": self.location,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "labour_cost": self.labour_cost,
            "parts_cost": self.parts_cost,
            "travel_cost": self.travel_cost,
            "other_cost": self.other_cost,
            "total_cost": self.total_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MaintenanceChecklistItem(db.Model):
    __tablename__ = "maintenance_checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("maintenance_work_orders.id"), nullable=False, index=True)
    label = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    work_order = db.relationship("MaintenanceWorkOrder", back_populates="checklist_items")


class MaintenancePart(db.Model):
    __tablename__ = "maintenance_parts"

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("maintenance_work_orders.id"), nullable=False, index=True)
    part_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_cost = db.Column(db.Float, default=0.0, nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    work_order = db.relationship("MaintenanceWorkOrder", back_populates="parts")

    @property
    def line_total(self) -> float:
        return float(self.quantity or 0) * float(self.unit_cost or 0)


class MaintenanceActivity(db.Model):
    __tablename__ = "maintenance_activities"

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("maintenance_work_orders.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(32), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    work_order = db.relationship("MaintenanceWorkOrder", back_populates="activities")
    actor = db.relationship("User", foreign_keys=[actor_user_id])


class MaintenancePlan(db.Model):
    """Recurring preventive maintenance templates."""

    __tablename__ = "maintenance_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    maintenance_type = db.Column(db.String(32), default="preventive", nullable=False)
    frequency = db.Column(db.String(32), default="monthly", nullable=False)
    interval_days = db.Column(db.Integer, default=30, nullable=False)
    linked_type = db.Column(db.String(32), nullable=True)  # optional scope filter
    checklist_template = db.Column(db.JSON, nullable=True)  # list of strings
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    next_run_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    work_orders = db.relationship("MaintenanceWorkOrder", back_populates="plan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "maintenance_type": self.maintenance_type,
            "frequency": self.frequency,
            "interval_days": self.interval_days,
            "linked_type": self.linked_type,
            "checklist_template": self.checklist_template or [],
            "is_active": self.is_active,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
        }
