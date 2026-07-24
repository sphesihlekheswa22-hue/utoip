"""enterprise it file repository tables

Revision ID: c4f91a2b7e10
Revises: b8e4f2a91c03
Create Date: 2026-07-24 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c4f91a2b7e10"
down_revision = "b8e4f2a91c03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repo_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_deletion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("repo_files", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_repo_files_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_repo_files_file_type"), ["file_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_repo_files_category"), ["category"], unique=False)

    op.create_table(
        "file_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "version", name="uq_file_version"),
    )
    with op.batch_alter_table("file_versions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_file_versions_file_id"), ["file_id"], unique=False)

    op.create_table(
        "file_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "link_type", "link_id", name="uq_file_link_target"),
    )
    with op.batch_alter_table("file_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_file_links_file_id"), ["file_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_file_links_link_type"), ["link_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_file_links_link_id"), ["link_id"], unique=False)

    op.create_table(
        "file_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "tag", name="uq_file_tag"),
    )
    with op.batch_alter_table("file_tags", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_file_tags_file_id"), ["file_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_file_tags_tag"), ["tag"], unique=False)

    op.create_table(
        "file_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("can_view", sa.Boolean(), nullable=False),
        sa.Column("can_download", sa.Boolean(), nullable=False),
        sa.Column("can_manage", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("file_permissions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_file_permissions_file_id"), ["file_id"], unique=False)

    op.create_table(
        "file_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("file_activities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_file_activities_file_id"), ["file_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_file_activities_activity_type"), ["activity_type"], unique=False)


def downgrade():
    with op.batch_alter_table("file_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_activities_activity_type"))
        batch_op.drop_index(batch_op.f("ix_file_activities_file_id"))
    op.drop_table("file_activities")

    with op.batch_alter_table("file_permissions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_permissions_file_id"))
    op.drop_table("file_permissions")

    with op.batch_alter_table("file_tags", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_tags_tag"))
        batch_op.drop_index(batch_op.f("ix_file_tags_file_id"))
    op.drop_table("file_tags")

    with op.batch_alter_table("file_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_links_link_id"))
        batch_op.drop_index(batch_op.f("ix_file_links_link_type"))
        batch_op.drop_index(batch_op.f("ix_file_links_file_id"))
    op.drop_table("file_links")

    with op.batch_alter_table("file_versions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_versions_file_id"))
    op.drop_table("file_versions")

    with op.batch_alter_table("repo_files", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_repo_files_category"))
        batch_op.drop_index(batch_op.f("ix_repo_files_file_type"))
        batch_op.drop_index(batch_op.f("ix_repo_files_name"))
    op.drop_table("repo_files")
