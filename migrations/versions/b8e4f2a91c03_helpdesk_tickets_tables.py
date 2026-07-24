"""helpdesk tickets tables

Revision ID: b8e4f2a91c03
Revises: 197c3232548a
Create Date: 2026-07-23 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b8e4f2a91c03"
down_revision = "197c3232548a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_number", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("requester_user_id", sa.Integer(), nullable=True),
        sa.Column("requester_name", sa.String(length=120), nullable=True),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("linked_type", sa.String(length=32), nullable=False),
        sa.Column("linked_id", sa.Integer(), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tickets_ticket_number"), ["ticket_number"], unique=True)
        batch_op.create_index(batch_op.f("ix_tickets_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_tickets_priority"), ["priority"], unique=False)

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ticket_comments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ticket_comments_ticket_id"), ["ticket_id"], unique=False)


def downgrade():
    with op.batch_alter_table("ticket_comments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ticket_comments_ticket_id"))
    op.drop_table("ticket_comments")
    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tickets_priority"))
        batch_op.drop_index(batch_op.f("ix_tickets_status"))
        batch_op.drop_index(batch_op.f("ix_tickets_ticket_number"))
    op.drop_table("tickets")
