"""Add agent_commands table for remote actions."""

from alembic import op
import sqlalchemy as sa


revision = "g8d41e2a9c70"
down_revision = "a8d35f6c2b54"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_commands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=True),
        sa.Column("command", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["computer_id"], ["computers.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("agent_commands", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_agent_commands_agent_id"), ["agent_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_agent_commands_command"), ["command"], unique=False)
        batch_op.create_index(batch_op.f("ix_agent_commands_computer_id"), ["computer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_agent_commands_status"), ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("agent_commands", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_agent_commands_status"))
        batch_op.drop_index(batch_op.f("ix_agent_commands_computer_id"))
        batch_op.drop_index(batch_op.f("ix_agent_commands_command"))
        batch_op.drop_index(batch_op.f("ix_agent_commands_agent_id"))
    op.drop_table("agent_commands")
