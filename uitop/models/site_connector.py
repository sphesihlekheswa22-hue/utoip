"""Site connectors — on-prem LAN scanners that push inventory to cloud UITOP."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SiteConnector(db.Model):
    __tablename__ = "site_connectors"

    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(120), nullable=False)
    connector_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    api_client_id = db.Column(db.Integer, db.ForeignKey("api_clients.id"), nullable=True, index=True)
    hostname = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    connector_version = db.Column(db.String(40), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="registered")
    cidrs_json = db.Column(db.JSON, nullable=True)
    last_scan_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_stats_json = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    api_client = db.relationship("ApiClient", backref=db.backref("site_connector", uselist=False))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "site_name": self.site_name,
            "connector_id": self.connector_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "connector_version": self.connector_version,
            "status": self.status,
            "cidrs": self.cidrs_json or [],
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "last_stats": self.last_stats_json or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
