"""Enterprise IT file repository — attachments linked to UITOP objects."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


FILE_CATEGORIES = (
    "Documentation",
    "Scripts",
    "Software",
    "Drivers",
    "Configurations",
    "Backups",
    "Reports",
    "Contracts",
    "Warranties",
    "Logs",
)

LINK_TYPES = (
    "computer",
    "server",
    "network_device",
    "printer",
    "asset",
    "vendor",
    "software",
    "contract",
    "ticket",
    "license",
)

ACTIVITY_TYPES = (
    "uploaded",
    "downloaded",
    "version_updated",
    "linked",
    "unlinked",
    "permission_changed",
    "previewed",
    "shared",
    "deleted",
    "scheduled_deletion",
)


class RepoFile(db.Model):
    """Logical file in the IT repository (current version metadata)."""

    __tablename__ = "repo_files"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(32), nullable=False, index=True)  # PDF, PS1, ZIP…
    mime_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.BigInteger, default=0, nullable=False)
    storage_path = db.Column(db.String(512), nullable=True)  # relative to FILES_ROOT
    category = db.Column(db.String(64), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, default=1, nullable=False)
    is_shared = db.Column(db.Boolean, default=False, nullable=False)
    storage_backend = db.Column(db.String(32), default="local", nullable=False)  # local|nas|azure|s3|gcs
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    scheduled_deletion_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])
    versions = db.relationship(
        "FileVersion",
        back_populates="file",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="FileVersion.version.desc()",
    )
    links = db.relationship(
        "FileLink",
        back_populates="file",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    tags = db.relationship(
        "FileTag",
        back_populates="file",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    permissions = db.relationship(
        "FilePermission",
        back_populates="file",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    activities = db.relationship(
        "FileActivity",
        back_populates="file",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="FileActivity.created_at.desc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "original_name": self.original_name,
            "type": self.file_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2) if self.size_bytes else 0,
            "category": self.category,
            "description": self.description,
            "version": self.version,
            "shared": self.is_shared,
            "storage_backend": self.storage_backend,
            "uploaded_by_id": self.uploaded_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "scheduled_deletion_at": (
                self.scheduled_deletion_at.isoformat() if self.scheduled_deletion_at else None
            ),
        }


class FileVersion(db.Model):
    __tablename__ = "file_versions"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("repo_files.id"), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    storage_path = db.Column(db.String(512), nullable=True)
    size_bytes = db.Column(db.BigInteger, default=0, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    file = db.relationship("RepoFile", back_populates="versions")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])

    __table_args__ = (db.UniqueConstraint("file_id", "version", name="uq_file_version"),)

    def to_dict(self):
        return {
            "id": self.id,
            "file_id": self.file_id,
            "version": self.version,
            "size_bytes": self.size_bytes,
            "note": self.note,
            "uploaded_by_id": self.uploaded_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FileLink(db.Model):
    """Attach a repository file to one or more UITOP objects."""

    __tablename__ = "file_links"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("repo_files.id"), nullable=False, index=True)
    link_type = db.Column(db.String(32), nullable=False, index=True)
    link_id = db.Column(db.Integer, nullable=False, index=True)
    label = db.Column(db.String(255), nullable=True)  # cached display name
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    file = db.relationship("RepoFile", back_populates="links")

    __table_args__ = (
        db.UniqueConstraint("file_id", "link_type", "link_id", name="uq_file_link_target"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "file_id": self.file_id,
            "type": self.link_type,
            "id_ref": self.link_id,
            "label": self.label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FileTag(db.Model):
    __tablename__ = "file_tags"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("repo_files.id"), nullable=False, index=True)
    tag = db.Column(db.String(64), nullable=False, index=True)

    file = db.relationship("RepoFile", back_populates="tags")

    __table_args__ = (db.UniqueConstraint("file_id", "tag", name="uq_file_tag"),)


class FilePermission(db.Model):
    """Who can see a file beyond IT defaults (role-scoped)."""

    __tablename__ = "file_permissions"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("repo_files.id"), nullable=False, index=True)
    role_name = db.Column(db.String(64), nullable=True)  # e.g. asset_manager, super_admin
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    can_view = db.Column(db.Boolean, default=True, nullable=False)
    can_download = db.Column(db.Boolean, default=True, nullable=False)
    can_manage = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    file = db.relationship("RepoFile", back_populates="permissions")
    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "role_name": self.role_name,
            "user_id": self.user_id,
            "can_view": self.can_view,
            "can_download": self.can_download,
            "can_manage": self.can_manage,
        }


class FileActivity(db.Model):
    __tablename__ = "file_activities"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("repo_files.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(32), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    file = db.relationship("RepoFile", back_populates="activities")
    actor = db.relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.activity_type,
            "message": self.message,
            "actor_user_id": self.actor_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
