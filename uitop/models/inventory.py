"""Inventory stub models (agent-ready)."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Computer(db.Model):
    __tablename__ = "computers"

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False, index=True)
    asset_tag = db.Column(db.String(64), nullable=True, unique=True)
    ip_address = db.Column(db.String(64), nullable=True)
    mac_address = db.Column(db.String(32), nullable=True)
    os_name = db.Column(db.String(120), nullable=True)
    os_version = db.Column(db.String(120), nullable=True)
    manufacturer = db.Column(db.String(120), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    serial_number = db.Column(db.String(120), nullable=True)
    domain = db.Column(db.String(255), nullable=True)
    cpu_model = db.Column(db.String(255), nullable=True)
    cpu_cores = db.Column(db.Integer, nullable=True)
    ram_gb = db.Column(db.Float, nullable=True)
    disk_gb = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(32), default="unknown", nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    agent_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    agent_version = db.Column(db.String(32), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    inventory_payload = db.Column(db.JSON, nullable=True)
    inventory_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = db.relationship("Department", backref=db.backref("computers", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "hostname": self.hostname,
            "asset_tag": self.asset_tag,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "domain": self.domain,
            "cpu_model": self.cpu_model,
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "disk_gb": self.disk_gb,
            "status": self.status,
            "department_id": self.department_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "inventory_updated_at": self.inventory_updated_at.isoformat() if self.inventory_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Server(db.Model):
    __tablename__ = "servers"

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False, index=True)
    asset_tag = db.Column(db.String(64), nullable=True, unique=True)
    ip_address = db.Column(db.String(64), nullable=True)
    os_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default="unknown", nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    agent_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    agent_version = db.Column(db.String(32), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = db.relationship("Department", backref=db.backref("servers", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "hostname": self.hostname,
            "asset_tag": self.asset_tag,
            "ip_address": self.ip_address,
            "os_name": self.os_name,
            "role": self.role,
            "status": self.status,
            "department_id": self.department_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NetworkDevice(db.Model):
    __tablename__ = "network_devices"

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True, index=True)
    mac_address = db.Column(db.String(32), nullable=True)
    device_type = db.Column(db.String(64), nullable=True)
    vendor = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(32), default="unknown", nullable=False)
    agent_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    agent_version = db.Column(db.String(32), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "device_type": self.device_type,
            "vendor": self.vendor,
            "status": self.status,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Printer(db.Model):
    __tablename__ = "printers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), default="unknown", nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    agent_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    agent_version = db.Column(db.String(32), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # SNMP telemetry
    snmp_profile_id = db.Column(db.Integer, db.ForeignKey("snmp_profiles.id"), nullable=True)
    toner_percent = db.Column(db.Integer, nullable=True)
    paper_percent = db.Column(db.Integer, nullable=True)
    queue_depth = db.Column(db.Integer, nullable=True)
    snmp_sys_descr = db.Column(db.String(512), nullable=True)
    snmp_payload = db.Column(db.JSON, nullable=True)
    last_snmp_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = db.relationship("Department", backref=db.backref("printers", lazy="dynamic"))
    snmp_profile = db.relationship("SnmpProfile", backref=db.backref("printers", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "model": self.model,
            "location": self.location,
            "status": self.status,
            "department_id": self.department_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "snmp_profile_id": self.snmp_profile_id,
            "toner_percent": self.toner_percent,
            "paper_percent": self.paper_percent,
            "queue_depth": self.queue_depth,
            "snmp_sys_descr": self.snmp_sys_descr,
            "last_snmp_at": self.last_snmp_at.isoformat() if self.last_snmp_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
