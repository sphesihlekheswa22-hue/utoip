"""workflow_engine_and_tasks

Revision ID: i2f8a91c0b33
Revises: cbb171cd6ca0
Create Date: 2026-07-27 10:52:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "i2f8a91c0b33"
down_revision = "cbb171cd6ca0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_definitions_key", "workflow_definitions", ["key"], unique=True)

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step_key", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("requester_user_id", sa.Integer(), nullable=True),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("resource_label", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["definition_id"], ["workflow_definitions.id"]),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_instances_definition_id", "workflow_instances", ["definition_id"])
    op.create_index("ix_workflow_instances_number", "workflow_instances", ["number"], unique=True)
    op.create_index("ix_workflow_instances_status", "workflow_instances", ["status"])
    op.create_index("ix_workflow_instances_current_step_key", "workflow_instances", ["current_step_key"])
    op.create_index("ix_workflow_instances_requester_user_id", "workflow_instances", ["requester_user_id"])
    op.create_index("ix_workflow_instances_assignee_user_id", "workflow_instances", ["assignee_user_id"])
    op.create_index("ix_workflow_instances_resource_type", "workflow_instances", ["resource_type"])

    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_events_instance_id", "workflow_events", ["instance_id"])
    op.create_index("ix_workflow_events_action", "workflow_events", ["action"])

    op.create_table(
        "work_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("workflow_instance_id", sa.Integer(), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("link_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_tasks_status", "work_tasks", ["status"])
    op.create_index("ix_work_tasks_priority", "work_tasks", ["priority"])
    op.create_index("ix_work_tasks_assignee_user_id", "work_tasks", ["assignee_user_id"])
    op.create_index("ix_work_tasks_due_at", "work_tasks", ["due_at"])
    op.create_index("ix_work_tasks_workflow_instance_id", "work_tasks", ["workflow_instance_id"])


def downgrade():
    op.drop_table("work_tasks")
    op.drop_table("workflow_events")
    op.drop_table("workflow_instances")
    op.drop_table("workflow_definitions")
