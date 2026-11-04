"""maintenance work orders and plans

Revision ID: e6b13d4f0a32
Revises: d5a82c3e9f21
Create Date: 2026-07-24 09:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e6b13d4f0a32"
down_revision = "d5a82c3e9f21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "maintenance_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("maintenance_type", sa.String(length=32), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("linked_type", sa.String(length=32), nullable=True),
        sa.Column("checklist_template", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "maintenance_work_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_order_number", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("maintenance_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("linked_type", sa.String(length=32), nullable=False),
        sa.Column("linked_id", sa.Integer(), nullable=True),
        sa.Column("linked_label", sa.String(length=255), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("technician_user_id", sa.Integer(), nullable=True),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("labour_cost", sa.Float(), nullable=False),
        sa.Column("parts_cost", sa.Float(), nullable=False),
        sa.Column("travel_cost", sa.Float(), nullable=False),
        sa.Column("other_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["maintenance_plans.id"]),
        sa.ForeignKeyConstraint(["technician_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["asset_vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("maintenance_work_orders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_work_order_number"), ["work_order_number"], unique=True)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_maintenance_type"), ["maintenance_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_priority"), ["priority"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_linked_type"), ["linked_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_linked_id"), ["linked_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_scheduled_at"), ["scheduled_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_work_orders_due_at"), ["due_at"], unique=False)

    op.create_table(
        "maintenance_checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("maintenance_checklist_items", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_maintenance_checklist_items_work_order_id"), ["work_order_id"], unique=False)

    op.create_table(
        "maintenance_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("part_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("maintenance_parts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_maintenance_parts_work_order_id"), ["work_order_id"], unique=False)

    op.create_table(
        "maintenance_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("maintenance_activities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_maintenance_activities_work_order_id"), ["work_order_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_maintenance_activities_activity_type"), ["activity_type"], unique=False)


def downgrade():
    with op.batch_alter_table("maintenance_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_maintenance_activities_activity_type"))
        batch_op.drop_index(batch_op.f("ix_maintenance_activities_work_order_id"))
    op.drop_table("maintenance_activities")

    with op.batch_alter_table("maintenance_parts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_maintenance_parts_work_order_id"))
    op.drop_table("maintenance_parts")

    with op.batch_alter_table("maintenance_checklist_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_maintenance_checklist_items_work_order_id"))
    op.drop_table("maintenance_checklist_items")

    with op.batch_alter_table("maintenance_work_orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_due_at"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_scheduled_at"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_linked_id"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_linked_type"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_priority"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_status"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_maintenance_type"))
        batch_op.drop_index(batch_op.f("ix_maintenance_work_orders_work_order_number"))
    op.drop_table("maintenance_work_orders")
    op.drop_table("maintenance_plans")
