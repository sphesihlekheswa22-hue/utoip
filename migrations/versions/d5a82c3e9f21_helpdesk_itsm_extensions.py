"""helpdesk itsm extensions

Revision ID: d5a82c3e9f21
Revises: c4f91a2b7e10
Create Date: 2026-07-24 09:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d5a82c3e9f21"
down_revision = "c4f91a2b7e10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ticket_type", sa.String(length=32), nullable=False, server_default="incident")
        )
        batch_op.add_column(sa.Column("problem_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_tickets_ticket_type"), ["ticket_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_tickets_problem_id"), ["problem_id"], unique=False)
        batch_op.create_foreign_key("fk_tickets_problem_id", "tickets", ["problem_id"], ["id"])

    op.create_table(
        "ticket_object_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "link_type", "link_id", name="uq_ticket_object_link"),
    )
    with op.batch_alter_table("ticket_object_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ticket_object_links_ticket_id"), ["ticket_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ticket_object_links_link_type"), ["link_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_ticket_object_links_link_id"), ["link_id"], unique=False)

    op.create_table(
        "ticket_time_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("technician_user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["technician_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ticket_time_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ticket_time_logs_ticket_id"), ["ticket_id"], unique=False)

    op.create_table(
        "ticket_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ticket_activities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ticket_activities_ticket_id"), ["ticket_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ticket_activities_activity_type"), ["activity_type"], unique=False)

    # Backfill object links from legacy linked_type/linked_id
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, linked_type, linked_id, created_at FROM tickets "
            "WHERE linked_type IS NOT NULL AND linked_type != 'none' AND linked_id IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        conn.execute(
            sa.text(
                "INSERT INTO ticket_object_links (ticket_id, link_type, link_id, label, created_at) "
                "VALUES (:tid, :lt, :lid, NULL, :ca)"
            ),
            {"tid": row[0], "lt": row[1], "lid": row[2], "ca": row[3]},
        )


def downgrade():
    with op.batch_alter_table("ticket_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ticket_activities_activity_type"))
        batch_op.drop_index(batch_op.f("ix_ticket_activities_ticket_id"))
    op.drop_table("ticket_activities")

    with op.batch_alter_table("ticket_time_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ticket_time_logs_ticket_id"))
    op.drop_table("ticket_time_logs")

    with op.batch_alter_table("ticket_object_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ticket_object_links_link_id"))
        batch_op.drop_index(batch_op.f("ix_ticket_object_links_link_type"))
        batch_op.drop_index(batch_op.f("ix_ticket_object_links_ticket_id"))
    op.drop_table("ticket_object_links")

    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tickets_problem_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_tickets_problem_id"))
        batch_op.drop_index(batch_op.f("ix_tickets_ticket_type"))
        batch_op.drop_column("problem_id")
        batch_op.drop_column("ticket_type")
