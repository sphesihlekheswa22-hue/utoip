"""SNMP profiles + printer telemetry columns."""

from alembic import op
import sqlalchemy as sa


revision = "h9e52f3b0d81"
down_revision = "g8d41e2a9c70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snmp_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column("community", sa.String(length=120), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=True),
        sa.Column("is_write", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("printers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("snmp_profile_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("toner_percent", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("paper_percent", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("queue_depth", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("snmp_sys_descr", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("snmp_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("last_snmp_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_printers_snmp_profile_id",
            "snmp_profiles",
            ["snmp_profile_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("printers", schema=None) as batch_op:
        batch_op.drop_constraint("fk_printers_snmp_profile_id", type_="foreignkey")
        batch_op.drop_column("last_snmp_at")
        batch_op.drop_column("snmp_payload")
        batch_op.drop_column("snmp_sys_descr")
        batch_op.drop_column("queue_depth")
        batch_op.drop_column("paper_percent")
        batch_op.drop_column("toner_percent")
        batch_op.drop_column("snmp_profile_id")
    op.drop_table("snmp_profiles")
