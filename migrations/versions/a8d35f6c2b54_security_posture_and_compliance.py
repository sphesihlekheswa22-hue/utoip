"""security posture and compliance tables

Revision ID: a8d35f6c2b54
Revises: f7c24e5b1a43
Create Date: 2026-07-24 10:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a8d35f6c2b54"
down_revision = "f7c24e5b1a43"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_security_postures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=False),
        sa.Column("antivirus_name", sa.String(length=120), nullable=True),
        sa.Column("antivirus_enabled", sa.Boolean(), nullable=False),
        sa.Column("antivirus_definitions_ok", sa.Boolean(), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firewall_enabled", sa.Boolean(), nullable=False),
        sa.Column("bitlocker_enabled", sa.Boolean(), nullable=False),
        sa.Column("windows_updated", sa.Boolean(), nullable=False),
        sa.Column("pending_updates", sa.Integer(), nullable=False),
        sa.Column("usb_storage_allowed", sa.Boolean(), nullable=False),
        sa.Column("compliance_score", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("computer_id"),
    )
    with op.batch_alter_table("device_security_postures", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_device_security_postures_computer_id"), ["computer_id"], unique=True)

    op.create_table(
        "security_threats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("threat_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_threats", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_threats_threat_type"), ["threat_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_threats_severity"), ["severity"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_threats_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_threats_computer_id"), ["computer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_threats_detected_at"), ["detected_at"], unique=False)

    op.create_table(
        "security_vulnerabilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("cve_id", sa.String(length=64), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_vulnerabilities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_vulnerabilities_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_vulnerabilities_severity"), ["severity"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_vulnerabilities_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_vulnerabilities_computer_id"), ["computer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_vulnerabilities_detected_at"), ["detected_at"], unique=False)

    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_number", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_incidents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_incidents_incident_number"), ["incident_number"], unique=True)
        batch_op.create_index(batch_op.f("ix_security_incidents_incident_type"), ["incident_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_incidents_severity"), ["severity"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_incidents_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_incidents_computer_id"), ["computer_id"], unique=False)

    op.create_table(
        "security_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("is_enforced", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_policies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_policies_key"), ["key"], unique=True)

    op.create_table(
        "security_user_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_user_activities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_user_activities_activity_type"), ["activity_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_user_activities_username"), ["username"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_user_activities_occurred_at"), ["occurred_at"], unique=False)

    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("security_audit_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_security_audit_events_event_type"), ["event_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_security_audit_events_occurred_at"), ["occurred_at"], unique=False)


def downgrade():
    with op.batch_alter_table("security_audit_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_audit_events_occurred_at"))
        batch_op.drop_index(batch_op.f("ix_security_audit_events_event_type"))
    op.drop_table("security_audit_events")

    with op.batch_alter_table("security_user_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_user_activities_occurred_at"))
        batch_op.drop_index(batch_op.f("ix_security_user_activities_username"))
        batch_op.drop_index(batch_op.f("ix_security_user_activities_activity_type"))
    op.drop_table("security_user_activities")

    with op.batch_alter_table("security_policies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_policies_key"))
    op.drop_table("security_policies")

    with op.batch_alter_table("security_incidents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_incidents_computer_id"))
        batch_op.drop_index(batch_op.f("ix_security_incidents_status"))
        batch_op.drop_index(batch_op.f("ix_security_incidents_severity"))
        batch_op.drop_index(batch_op.f("ix_security_incidents_incident_type"))
        batch_op.drop_index(batch_op.f("ix_security_incidents_incident_number"))
    op.drop_table("security_incidents")

    with op.batch_alter_table("security_vulnerabilities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_vulnerabilities_detected_at"))
        batch_op.drop_index(batch_op.f("ix_security_vulnerabilities_computer_id"))
        batch_op.drop_index(batch_op.f("ix_security_vulnerabilities_status"))
        batch_op.drop_index(batch_op.f("ix_security_vulnerabilities_severity"))
        batch_op.drop_index(batch_op.f("ix_security_vulnerabilities_category"))
    op.drop_table("security_vulnerabilities")

    with op.batch_alter_table("security_threats", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_security_threats_detected_at"))
        batch_op.drop_index(batch_op.f("ix_security_threats_computer_id"))
        batch_op.drop_index(batch_op.f("ix_security_threats_status"))
        batch_op.drop_index(batch_op.f("ix_security_threats_severity"))
        batch_op.drop_index(batch_op.f("ix_security_threats_threat_type"))
    op.drop_table("security_threats")

    with op.batch_alter_table("device_security_postures", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_device_security_postures_computer_id"))
    op.drop_table("device_security_postures")
