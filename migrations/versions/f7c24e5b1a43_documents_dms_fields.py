"""documents DMS fields on repo_files

Revision ID: f7c24e5b1a43
Revises: e6b13d4f0a32
Create Date: 2026-07-24 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f7c24e5b1a43"
down_revision = "e6b13d4f0a32"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("repo_files", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.String(length=32), nullable=False, server_default="document"))
        batch_op.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="published"))
        batch_op.add_column(sa.Column("owner_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("version_label", sa.String(length=32), nullable=True))
        batch_op.create_index(batch_op.f("ix_repo_files_kind"), ["kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_repo_files_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_repo_files_expires_at"), ["expires_at"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_repo_files_owner_user_id_users"),
            "users",
            ["owner_user_id"],
            ["id"],
        )

    op.create_table(
        "document_approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_approvals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_approvals_file_id"), ["file_id"], unique=False)

    # Classify existing rows: attachment-like vs documents
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE repo_files
            SET kind = 'attachment'
            WHERE category IN ('Scripts', 'Drivers', 'Logs', 'Software')
               OR lower(name) LIKE '%.dmp'
               OR lower(name) LIKE '%.evtx'
               OR lower(name) LIKE '%photo%'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE repo_files
            SET category = CASE category
                WHEN 'Documentation' THEN 'Manuals'
                WHEN 'Configurations' THEN 'Infrastructure'
                ELSE category
            END
            WHERE kind = 'document'
              AND category IN ('Documentation', 'Configurations')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE repo_files
            SET version_label = CAST(version AS TEXT) || '.0'
            WHERE version_label IS NULL
            """
        )
    )


def downgrade():
    with op.batch_alter_table("document_approvals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_document_approvals_file_id"))
    op.drop_table("document_approvals")

    with op.batch_alter_table("repo_files", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_repo_files_owner_user_id_users"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_repo_files_expires_at"))
        batch_op.drop_index(batch_op.f("ix_repo_files_status"))
        batch_op.drop_index(batch_op.f("ix_repo_files_kind"))
        batch_op.drop_column("version_label")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("owner_user_id")
        batch_op.drop_column("owner_name")
        batch_op.drop_column("status")
        batch_op.drop_column("kind")
