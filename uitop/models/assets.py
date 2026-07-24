"""Asset management models — lifecycle / ownership layer over tech inventory."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# Lifecycle statuses
ASSET_STATUSES = (
    "ordered",
    "in_store",
    "assigned",
    "in_use",
    "in_repair",
    "disposed",
)

# Polymorphic link targets
LINK_TYPES = ("computer", "server", "network_device", "printer", "none")


class AssetCategory(db.Model):
    __tablename__ = "asset_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    is_it = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    assets = db.relationship("Asset", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_it": self.is_it,
        }


class AssetVendor(db.Model):
    __tablename__ = "asset_vendors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    contact_email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(64), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    assets = db.relationship("Asset", back_populates="vendor", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "website": self.website,
        }


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), default="in_store", nullable=False, index=True)
    serial_number = db.Column(db.String(120), nullable=True, index=True)
    location = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("asset_categories.id"), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("asset_vendors.id"), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    custodian_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Link to operational inventory (optional)
    linked_type = db.Column(db.String(32), default="none", nullable=False, index=True)
    linked_id = db.Column(db.Integer, nullable=True, index=True)

    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=True)
    warranty_expires = db.Column(db.Date, nullable=True)
    po_number = db.Column(db.String(64), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    category = db.relationship("AssetCategory", back_populates="assets")
    vendor = db.relationship("AssetVendor", back_populates="assets")
    department = db.relationship("Department")
    custodian = db.relationship("User", foreign_keys=[custodian_user_id])
    assignments = db.relationship(
        "AssetAssignment",
        back_populates="asset",
        lazy="dynamic",
    )
    requests = db.relationship("AssetRequest", back_populates="fulfilled_asset", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_tag": self.asset_tag,
            "name": self.name,
            "status": self.status,
            "serial_number": self.serial_number,
            "location": self.location,
            "notes": self.notes,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "vendor_id": self.vendor_id,
            "vendor": self.vendor.name if self.vendor else None,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "custodian_user_id": self.custodian_user_id,
            "custodian": self.custodian.full_name if self.custodian else None,
            "linked_type": self.linked_type,
            "linked_id": self.linked_id,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_cost": self.purchase_cost,
            "warranty_expires": self.warranty_expires.isoformat() if self.warranty_expires else None,
            "po_number": self.po_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssetAssignment(db.Model):
    __tablename__ = "asset_assignments"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assignee_name = db.Column(db.String(120), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    assigned_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    returned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    asset = db.relationship("Asset", back_populates="assignments")
    user = db.relationship("User", foreign_keys=[user_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])
    department = db.relationship("Department")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "user_id": self.user_id,
            "assignee_name": self.assignee_name or (self.user.full_name if self.user else None),
            "department": self.department.name if self.department else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "returned_at": self.returned_at.isoformat() if self.returned_at else None,
            "notes": self.notes,
        }


class AssetRequest(db.Model):
    __tablename__ = "asset_requests"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("asset_categories.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    justification = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="pending", nullable=False, index=True)
    # pending | approved | rejected | fulfilled | cancelled
    fulfilled_asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    requester = db.relationship("User", foreign_keys=[requester_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])
    category = db.relationship("AssetCategory")
    fulfilled_asset = db.relationship("Asset", back_populates="requests")

    def to_dict(self):
        return {
            "id": self.id,
            "requester": self.requester.full_name if self.requester else None,
            "category": self.category.name if self.category else None,
            "title": self.title,
            "justification": self.justification,
            "status": self.status,
            "fulfilled_asset_id": self.fulfilled_asset_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
