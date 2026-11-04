"""site_connectors

Revision ID: j3a92b0d1c44
Revises: i2f8a91c0b33
Create Date: 2026-07-27 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "j3a92b0d1c44"
down_revision = "i2f8a91c0b33"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_connectors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_name", sa.String(length=120), nullable=False),
        sa.Column("connector_id", sa.String(length=64), nullable=False),
        sa.Column("api_client_id", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("connector_version", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("cidrs_json", sa.JSON(), nullable=True),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stats_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_client_id"], ["api_clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_connectors_connector_id", "site_connectors", ["connector_id"], unique=True)
    op.create_index("ix_site_connectors_api_client_id", "site_connectors", ["api_client_id"], unique=False)


def downgrade():
    op.drop_index("ix_site_connectors_api_client_id", table_name="site_connectors")
    op.drop_index("ix_site_connectors_connector_id", table_name="site_connectors")
    op.drop_table("site_connectors")
