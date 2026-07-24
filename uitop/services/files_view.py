"""Enterprise IT File Repository — attachments linked to UITOP objects."""
from __future__ import annotations

import mimetypes
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from sqlalchemy import func, or_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from uitop.extensions import db
from uitop.models.assets import Asset, AssetVendor
from uitop.models.files import (
    FILE_CATEGORIES,
    LINK_TYPES,
    FileActivity,
    FileLink,
    FilePermission,
    FileTag,
    FileVersion,
    RepoFile,
)
from uitop.models.helpdesk import Ticket
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User

CATEGORIES = list(FILE_CATEGORIES)

CATEGORY_META = {
    "Documentation": {"icon": "fa-book", "hint": "Manuals, diagrams, runbooks"},
    "Scripts": {"icon": "fa-terminal", "hint": "PowerShell, Bash, automation"},
    "Software": {"icon": "fa-cube", "hint": "Installers and packages"},
    "Drivers": {"icon": "fa-microchip", "hint": "Device driver packages"},
    "Configurations": {"icon": "fa-sliders", "hint": "Switch, router, server configs"},
    "Backups": {"icon": "fa-hard-drive", "hint": "Backup archives and metadata"},
    "Reports": {"icon": "fa-chart-column", "hint": "Audits and diagnostics"},
    "Contracts": {"icon": "fa-file-contract", "hint": "Vendor and maintenance contracts"},
    "Warranties": {"icon": "fa-shield-halved", "hint": "Warranty certificates"},
    "Logs": {"icon": "fa-scroll", "hint": "Event logs, dumps, traces"},
}

PREVIEWABLE = {"PDF", "PNG", "JPG", "JPEG", "GIF", "WEBP", "TXT", "LOG", "CSV", "XML", "JSON", "PS1", "BAT", "SH", "MD"}


def utcnow():
    return datetime.now(timezone.utc)


def files_root() -> Path:
    root = Path(current_app.config.get("FILES_ROOT") or (Path(current_app.instance_path) / "repo_files"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def ext_type(filename: str) -> str:
    name = (filename or "").rsplit(".", 1)
    if len(name) < 2:
        return "FILE"
    return name[-1].upper()[:16]


def format_size(size_bytes: int | None) -> str:
    n = int(size_bytes or 0)
    if n >= 1024**3:
        return f"{n / (1024 ** 3):.2f} GB"
    if n >= 1024**2:
        return f"{n / (1024 ** 2):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def link_url(link_type: str, link_id: int) -> str | None:
    mapping = {
        "computer": f"/computers/{link_id}",
        "server": f"/servers/{link_id}",
        "network_device": f"/network/{link_id}",
        "printer": f"/printers/{link_id}",
        "asset": f"/assets/{link_id}",
        "vendor": f"/vendors/{link_id}",
        "software": f"/software/{link_id}",
        "ticket": f"/helpdesk/{link_id}",
        "license": f"/licenses/{link_id}",
        "contract": f"/vendors/{link_id}",
    }
    return mapping.get(link_type)


def resolve_link_label(link_type: str, link_id: int, fallback: str | None = None) -> str:
    if fallback:
        return fallback
    if link_type == "computer":
        row = Computer.query.get(link_id)
        return row.hostname if row else f"Computer #{link_id}"
    if link_type == "server":
        row = Server.query.get(link_id)
        return row.hostname if row else f"Server #{link_id}"
    if link_type == "network_device":
        row = NetworkDevice.query.get(link_id)
        return row.hostname if row else f"Network #{link_id}"
    if link_type == "printer":
        row = Printer.query.get(link_id)
        return row.name if row else f"Printer #{link_id}"
    if link_type == "asset":
        row = Asset.query.get(link_id)
        return row.asset_tag if row else f"Asset #{link_id}"
    if link_type == "vendor":
        row = AssetVendor.query.get(link_id)
        if row:
            return row.name
        # Mock vendor catalog IDs still work as labels
        return f"Vendor #{link_id}"
    if link_type == "ticket":
        row = Ticket.query.get(link_id)
        return row.ticket_number if row else f"Ticket #{link_id}"
    if link_type == "software":
        return f"Software #{link_id}"
    if link_type == "contract":
        return f"Contract #{link_id}"
    if link_type == "license":
        return f"License #{link_id}"
    return f"{link_type} #{link_id}"


def serialize_link(link: FileLink) -> dict:
    return {
        "id": link.id,
        "type": link.link_type,
        "object_id": link.link_id,
        "label": link.label or resolve_link_label(link.link_type, link.link_id),
        "url": link_url(link.link_type, link.link_id),
    }


def serialize_file(f: RepoFile, *, primary_link_only: bool = False) -> dict:
    tags = [t.tag for t in f.tags.order_by(FileTag.tag).all()]
    links = [serialize_link(l) for l in f.links.order_by(FileLink.created_at.asc()).all()]
    uploader = f.uploaded_by.full_name if f.uploaded_by else "System"
    data = {
        "id": f.id,
        "name": f.name,
        "category": f.category,
        "type": f.file_type,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "size_mb": round((f.size_bytes or 0) / (1024 * 1024), 2),
        "size_label": format_size(f.size_bytes),
        "uploaded": f.created_at.strftime("%Y-%m-%d") if f.created_at else "",
        "uploaded_at": f.created_at.isoformat() if f.created_at else None,
        "uploaded_by": uploader,
        "shared": f.is_shared,
        "tags": tags,
        "version": f.version,
        "description": f.description or "",
        "previewable": (f.file_type or "").upper() in PREVIEWABLE and bool(f.storage_path),
        "storage_backend": f.storage_backend,
        "has_blob": bool(f.storage_path),
        "links": links,
        "linked": links[0] if links else None,
    }
    if primary_link_only and links:
        data["linked"] = links[0]
    return data


def log_activity(file_id: int, activity_type: str, message: str | None = None, actor_id: int | None = None) -> None:
    db.session.add(
        FileActivity(
            file_id=file_id,
            activity_type=activity_type,
            message=message,
            actor_user_id=actor_id,
        )
    )


def get_file_or_none(file_id: int) -> RepoFile | None:
    return RepoFile.query.filter_by(id=file_id, is_deleted=False).first()


def set_tags(file: RepoFile, tags: list[str] | str | None) -> None:
    if isinstance(tags, str):
        raw = [t.strip() for t in re.split(r"[,;]+", tags) if t.strip()]
    else:
        raw = [t.strip() for t in (tags or []) if t and str(t).strip()]
    seen = set()
    cleaned = []
    for t in raw:
        key = t.lower()[:64]
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(t[:64])
    FileTag.query.filter_by(file_id=file.id).delete()
    for t in cleaned:
        db.session.add(FileTag(file_id=file.id, tag=t))


def add_link(
    file: RepoFile,
    link_type: str,
    link_id: int,
    *,
    label: str | None = None,
    actor_id: int | None = None,
) -> FileLink | None:
    if link_type not in LINK_TYPES or not link_id:
        return None
    existing = FileLink.query.filter_by(file_id=file.id, link_type=link_type, link_id=link_id).first()
    if existing:
        return existing
    resolved = resolve_link_label(link_type, link_id, label)
    link = FileLink(file_id=file.id, link_type=link_type, link_id=link_id, label=resolved)
    db.session.add(link)
    log_activity(file.id, "linked", f"Linked to {link_type}: {resolved}", actor_id)
    return link


def list_files_for_object(link_type: str, link_id: int) -> list[dict]:
    rows = (
        RepoFile.query.join(FileLink, FileLink.file_id == RepoFile.id)
        .filter(
            RepoFile.is_deleted.is_(False),
            FileLink.link_type == link_type,
            FileLink.link_id == link_id,
        )
        .order_by(RepoFile.created_at.desc())
        .all()
    )
    return [serialize_file(f) for f in rows]


def search_files(q: str | None = None, category: str | None = None, limit: int = 200) -> list[RepoFile]:
    query = RepoFile.query.filter_by(is_deleted=False)
    if category:
        query = query.filter(RepoFile.category == category)
    if q:
        term = f"%{q.strip()}%"
        query = (
            query.outerjoin(FileTag, FileTag.file_id == RepoFile.id)
            .outerjoin(FileLink, FileLink.file_id == RepoFile.id)
            .filter(
                or_(
                    RepoFile.name.ilike(term),
                    RepoFile.description.ilike(term),
                    RepoFile.file_type.ilike(term),
                    FileTag.tag.ilike(term),
                    FileLink.label.ilike(term),
                )
            )
            .distinct()
        )
    return query.order_by(RepoFile.created_at.desc()).limit(limit).all()


def kpis() -> dict:
    base = RepoFile.query.filter_by(is_deleted=False)
    total = base.count()
    storage = db.session.query(func.coalesce(func.sum(RepoFile.size_bytes), 0)).filter(
        RepoFile.is_deleted.is_(False)
    ).scalar() or 0
    since = utcnow() - timedelta(days=7)
    recent = base.filter(RepoFile.created_at >= since).count()
    shared = base.filter(RepoFile.is_shared.is_(True)).count()
    scripts = base.filter(RepoFile.category == "Scripts").count()
    docs = base.filter(RepoFile.category == "Documentation").count()
    backups = base.filter(RepoFile.category == "Backups").count()
    return {
        "total": total,
        "storage_bytes": int(storage),
        "storage_gb": round(int(storage) / (1024**3), 2),
        "storage_label": format_size(int(storage)),
        "recent_uploads": recent,
        "shared": shared,
        "scripts": scripts,
        "documents": docs,
        "backups": backups,
    }


def category_counts() -> list[dict]:
    rows = (
        db.session.query(RepoFile.category, func.count(RepoFile.id))
        .filter(RepoFile.is_deleted.is_(False))
        .group_by(RepoFile.category)
        .all()
    )
    by_cat = {c: n for c, n in rows}
    out = []
    for cat in CATEGORIES:
        meta = CATEGORY_META.get(cat, {})
        out.append(
            {
                "name": cat,
                "count": by_cat.get(cat, 0),
                "icon": meta.get("icon", "fa-folder"),
                "hint": meta.get("hint", ""),
            }
        )
    return out


def build_module_payload(*, q: str | None = None, category: str | None = None) -> dict:
    rows = search_files(q=q, category=category)
    return {
        "kpis": kpis(),
        "files": [serialize_file(f) for f in rows],
        "categories": CATEGORIES,
        "category_counts": category_counts(),
        "link_types": list(LINK_TYPES),
        "q": q or "",
        "category": category or "",
    }


def build_detail_payload(file_id: int) -> dict | None:
    f = get_file_or_none(file_id)
    if not f:
        return None
    versions = []
    for v in f.versions.order_by(FileVersion.version.desc()).all():
        by = v.uploaded_by.full_name if v.uploaded_by else "System"
        versions.append(
            {
                "version": v.version,
                "date": v.created_at.strftime("%Y-%m-%d") if v.created_at else "",
                "by": by,
                "note": v.note or ("Current" if v.version == f.version else ""),
                "size_label": format_size(v.size_bytes),
            }
        )
    perms = []
    for p in f.permissions.all():
        perms.append(
            {
                "role_name": p.role_name,
                "user": p.user.full_name if p.user else None,
                "can_view": p.can_view,
                "can_download": p.can_download,
                "can_manage": p.can_manage,
            }
        )
    if not perms:
        perms = [
            {
                "role_name": "IT Operators",
                "user": None,
                "can_view": True,
                "can_download": True,
                "can_manage": True,
            }
        ]
        if f.is_shared:
            perms.append(
                {
                    "role_name": "Linked object owners",
                    "user": None,
                    "can_view": True,
                    "can_download": True,
                    "can_manage": False,
                }
            )
    activities = []
    for a in f.activities.limit(40).all():
        actor = a.actor.full_name if a.actor else "System"
        activities.append(
            {
                "type": a.activity_type,
                "message": a.message or a.activity_type.replace("_", " ").title(),
                "actor": actor,
                "when": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
            }
        )
    return {
        "file": serialize_file(f),
        "versions": versions,
        "permissions": perms,
        "activities": activities,
        "links": [serialize_link(l) for l in f.links.all()],
    }


def _write_upload(file_id: int, version: int, upload: FileStorage) -> tuple[str, int]:
    safe = secure_filename(upload.filename or f"file-{file_id}")
    folder = files_root() / str(file_id)
    folder.mkdir(parents=True, exist_ok=True)
    rel = f"{file_id}/v{version}_{safe}"
    dest = files_root() / rel
    upload.save(dest)
    size = dest.stat().st_size
    return rel.replace("\\", "/"), size


def create_file_from_upload(
    upload: FileStorage,
    *,
    category: str,
    description: str | None = None,
    tags: str | None = None,
    is_shared: bool = False,
    actor_id: int | None = None,
    links: list[tuple[str, int]] | None = None,
    note: str | None = None,
) -> RepoFile:
    if not upload or not upload.filename:
        raise ValueError("A file is required")
    category = category if category in CATEGORIES else "Documentation"
    name = upload.filename
    ftype = ext_type(name)
    mime = upload.mimetype or mimetypes.guess_type(name)[0]

    f = RepoFile(
        name=name,
        original_name=name,
        file_type=ftype,
        mime_type=mime,
        size_bytes=0,
        category=category,
        description=(description or "").strip() or None,
        version=1,
        is_shared=bool(is_shared),
        storage_backend="local",
        uploaded_by_id=actor_id,
    )
    db.session.add(f)
    db.session.flush()

    rel, size = _write_upload(f.id, 1, upload)
    f.storage_path = rel
    f.size_bytes = size

    db.session.add(
        FileVersion(
            file_id=f.id,
            version=1,
            storage_path=rel,
            size_bytes=size,
            note=note or "Initial upload",
            uploaded_by_id=actor_id,
        )
    )
    set_tags(f, tags)
    for link_type, link_id in links or []:
        add_link(f, link_type, int(link_id), actor_id=actor_id)
    log_activity(f.id, "uploaded", f"Uploaded {name}", actor_id)
    db.session.commit()
    return f


def add_new_version(
    file_id: int,
    upload: FileStorage,
    *,
    note: str | None = None,
    actor_id: int | None = None,
) -> RepoFile:
    f = get_file_or_none(file_id)
    if not f:
        raise ValueError("File not found")
    if not upload or not upload.filename:
        raise ValueError("A file is required")
    new_ver = f.version + 1
    rel, size = _write_upload(f.id, new_ver, upload)
    f.version = new_ver
    f.storage_path = rel
    f.size_bytes = size
    f.name = upload.filename or f.name
    f.original_name = upload.filename or f.original_name
    f.file_type = ext_type(f.name)
    f.mime_type = upload.mimetype or f.mime_type
    f.updated_at = utcnow()
    db.session.add(
        FileVersion(
            file_id=f.id,
            version=new_ver,
            storage_path=rel,
            size_bytes=size,
            note=note or f"Version {new_ver}",
            uploaded_by_id=actor_id,
        )
    )
    log_activity(f.id, "version_updated", f"Version {new_ver} uploaded", actor_id)
    db.session.commit()
    return f


def absolute_path(f: RepoFile) -> Path | None:
    if not f.storage_path:
        return None
    path = files_root() / f.storage_path
    return path if path.is_file() else None


def seed_sample_repository(*, actor_id: int | None = None) -> int:
    """Create demo repository metadata (+ small placeholder blobs) if empty."""
    if RepoFile.query.count() > 0:
        return 0

    computer = Computer.query.order_by(Computer.id).first()
    server = Server.query.order_by(Server.id).first()
    asset = Asset.query.order_by(Asset.id).first()
    vendor = AssetVendor.query.order_by(AssetVendor.id).first()
    ticket = Ticket.query.order_by(Ticket.id).first()
    admin = User.query.filter_by(id=actor_id).first() if actor_id else User.query.order_by(User.id).first()
    uploader_id = admin.id if admin else None

    samples = [
        {
            "name": "SRV-001-Backup.zip",
            "category": "Backups",
            "type": "ZIP",
            "size": 1_840_000_000,
            "shared": False,
            "tags": ["backup", "server", "critical"],
            "description": "Daily full backup archive for the primary application server.",
            "links": [("server", server.id if server else 1), ("asset", asset.id if asset else 1)],
            "versions": 1,
            "perms": [("super_admin", True)],
        },
        {
            "name": "Network-Configuration.txt",
            "category": "Configurations",
            "type": "TXT",
            "size": 12_400,
            "shared": True,
            "tags": ["cisco", "network", "vlan"],
            "description": "Core switch uplink and VLAN documentation.",
            "links": [("server", server.id if server else 1)],
            "versions": 3,
            "content": "# UITOP Network Configuration\nVLAN 10 = Corp\nVLAN 20 = Servers\nVLAN 40 = Guest\n",
        },
        {
            "name": "Windows-Server-License.pdf",
            "category": "Contracts",
            "type": "PDF",
            "size": 420_000,
            "shared": False,
            "tags": ["license", "windows", "server"],
            "description": "Windows Server license certificate.",
            "links": [("server", server.id if server else 1)],
            "versions": 1,
        },
        {
            "name": "Recovery-Guide.pdf",
            "category": "Documentation",
            "type": "PDF",
            "size": 890_000,
            "shared": True,
            "tags": ["recovery", "server", "critical"],
            "description": "Bare-metal recovery steps for SRV hosts.",
            "links": [("server", server.id if server else 1)],
            "versions": 2,
        },
        {
            "name": "enroll-agent.ps1",
            "category": "Scripts",
            "type": "PS1",
            "size": 2400,
            "shared": True,
            "tags": ["powershell", "agent", "windows"],
            "description": "Silent UITOP agent enrollment helper.",
            "links": [("computer", computer.id if computer else 1)],
            "versions": 4,
            "content": "# UITOP agent enrollment\nparam([string]$Token)\nWrite-Host \"Enrolling with token...\"\n",
        },
        {
            "name": "Windows-Event-Log.evtx",
            "category": "Logs",
            "type": "EVTX",
            "size": 8_200_000,
            "shared": False,
            "tags": ["windows", "log", "diagnostics"],
            "description": "Exported System event log for crash analysis.",
            "links": [("computer", computer.id if computer else 1)],
            "versions": 1,
        },
        {
            "name": "Memory-Dump.dmp",
            "category": "Logs",
            "type": "DMP",
            "size": 268_435_456,
            "shared": False,
            "tags": ["crash", "dump", "windows"],
            "description": "Memory dump pending analysis.",
            "links": [("computer", computer.id if computer else 1)],
            "versions": 1,
        },
        {
            "name": "Driver-Package.zip",
            "category": "Drivers",
            "type": "ZIP",
            "size": 45_000_000,
            "shared": False,
            "tags": ["driver", "dell"],
            "description": "Approved chipset driver package.",
            "links": [("computer", computer.id if computer else 1), ("vendor", 1)],
            "versions": 1,
            "link_labels": {"vendor": "Dell Technologies"},
        },
        {
            "name": "Dell-Warranty.pdf",
            "category": "Warranties",
            "type": "PDF",
            "size": 380_000,
            "shared": False,
            "tags": ["dell", "warranty"],
            "description": "Hardware warranty certificate.",
            "links": [
                ("vendor", 1),
                ("asset", asset.id if asset else 1),
            ],
            "versions": 1,
            "perms": [("asset_manager", True), ("super_admin", True)],
            "link_labels": {"vendor": "Dell Technologies"},
        },
        {
            "name": "Purchase-Invoice.pdf",
            "category": "Contracts",
            "type": "PDF",
            "size": 220_000,
            "shared": False,
            "tags": ["invoice", "finance", "dell"],
            "description": "Purchase invoice for delivered hardware.",
            "links": [
                ("vendor", 1),
                ("asset", asset.id if asset else 1),
            ],
            "versions": 1,
            "perms": [("asset_manager", True), ("super_admin", True)],
            "link_labels": {"vendor": "Dell Technologies"},
        },
        {
            "name": "Maintenance-Contract.pdf",
            "category": "Contracts",
            "type": "PDF",
            "size": 1_100_000,
            "shared": False,
            "tags": ["contract", "dell", "critical"],
            "description": "Annual maintenance and support contract.",
            "links": [("vendor", 1)],
            "versions": 1,
            "perms": [("asset_manager", True), ("super_admin", True)],
            "link_labels": {"vendor": "Dell Technologies"},
        },
        {
            "name": "Office-Installer.exe",
            "category": "Software",
            "type": "EXE",
            "size": 980_000_000,
            "shared": False,
            "tags": ["microsoft", "office", "installer"],
            "description": "Approved Microsoft Office installer for deployment.",
            "links": [("software", 1)],
            "versions": 2,
            "link_labels": {"software": "Microsoft Office"},
        },
        {
            "name": "Office-Deploy.ps1",
            "category": "Scripts",
            "type": "PS1",
            "size": 3100,
            "shared": True,
            "tags": ["powershell", "office", "deploy"],
            "description": "Silent Office deployment script.",
            "links": [("software", 1)],
            "versions": 2,
            "content": "# Deploy Microsoft Office\nStart-Process setup.exe -ArgumentList '/configure config.xml' -Wait\n",
            "link_labels": {"software": "Microsoft Office"},
        },
        {
            "name": "Office-Configuration.xml",
            "category": "Configurations",
            "type": "XML",
            "size": 4200,
            "shared": True,
            "tags": ["office", "config"],
            "description": "Office Click-to-Run configuration.",
            "links": [("software", 1)],
            "versions": 1,
            "content": "<Configuration>\n  <Add OfficeClientEdition=\"64\" />\n</Configuration>\n",
            "link_labels": {"software": "Microsoft Office"},
        },
        {
            "name": "Cisco-Switch-Config.txt",
            "category": "Configurations",
            "type": "TXT",
            "size": 18_000,
            "shared": True,
            "tags": ["cisco", "switch", "network"],
            "description": "Running config export for core switch.",
            "links": [("network_device", 1)],
            "versions": 3,
            "content": "hostname CORE-SW-01\n!\nvlan 10\n name CORP\n!\n",
        },
        {
            "name": "HD-Diagnostic.zip",
            "category": "Reports",
            "type": "ZIP",
            "size": 12_500_000,
            "shared": False,
            "tags": ["helpdesk", "diagnostic"],
            "description": "VPN diagnostics package from helpdesk.",
            "links": [("ticket", ticket.id if ticket else 1)],
            "versions": 1,
        },
        {
            "name": "Disaster-Recovery-Plan-2026.pdf",
            "category": "Documentation",
            "type": "PDF",
            "size": 5_100_000,
            "shared": True,
            "tags": ["dr", "critical", "documentation"],
            "description": "Municipal ICT disaster recovery runbook.",
            "links": [],
            "versions": 5,
        },
        {
            "name": "Asset-Delivery-Note.pdf",
            "category": "Documentation",
            "type": "PDF",
            "size": 180_000,
            "shared": False,
            "tags": ["delivery", "asset"],
            "description": "Delivery note for received asset.",
            "links": [("asset", asset.id if asset else 1)],
            "versions": 1,
        },
        {
            "name": "Asset-Photo.jpg",
            "category": "Documentation",
            "type": "JPG",
            "size": 2_400_000,
            "shared": False,
            "tags": ["photo", "asset"],
            "description": "Asset condition photo on receipt.",
            "links": [("asset", asset.id if asset else 1)],
            "versions": 1,
        },
    ]

    created = 0
    root = Path(current_app.config.get("FILES_ROOT") or (Path(current_app.instance_path) / "repo_files"))
    root.mkdir(parents=True, exist_ok=True)

    for sample in samples:
        f = RepoFile(
            name=sample["name"],
            original_name=sample["name"],
            file_type=sample["type"],
            mime_type=mimetypes.guess_type(sample["name"])[0],
            size_bytes=sample["size"],
            category=sample["category"],
            description=sample["description"],
            version=sample["versions"],
            is_shared=sample["shared"],
            storage_backend="local",
            uploaded_by_id=uploader_id,
            created_at=utcnow() - timedelta(days=max(0, 10 - created)),
        )
        db.session.add(f)
        db.session.flush()

        folder = root / str(f.id)
        folder.mkdir(parents=True, exist_ok=True)
        content = sample.get("content")
        if content is None:
            content = f"UITOP repository placeholder for {sample['name']}\n"
        # Keep last version as current blob; earlier versions as stubs
        for ver in range(1, sample["versions"] + 1):
            rel = f"{f.id}/v{ver}_{secure_filename(sample['name'])}"
            path = root / rel
            if ver == sample["versions"]:
                path.write_text(content if isinstance(content, str) else content.decode(), encoding="utf-8")
                f.storage_path = rel.replace("\\", "/")
                # Keep declared size for estate storage KPIs (demo binaries are placeholders)
                f.size_bytes = sample["size"]
                size = path.stat().st_size if sample["type"] in {"TXT", "PS1", "XML", "LOG", "MD", "CSV", "JSON"} else sample["size"]
            else:
                path.write_text(f"Version {ver} of {sample['name']}\n", encoding="utf-8")
                size = path.stat().st_size
            db.session.add(
                FileVersion(
                    file_id=f.id,
                    version=ver,
                    storage_path=rel.replace("\\", "/"),
                    size_bytes=sample["size"] if ver == sample["versions"] else size,
                    note="Initial upload" if ver == 1 else f"Revision {ver}",
                    uploaded_by_id=uploader_id,
                    created_at=utcnow() - timedelta(days=(sample["versions"] - ver) * 30),
                )
            )

        set_tags(f, sample["tags"])
        labels = sample.get("link_labels") or {}
        for link_type, link_id in sample.get("links") or []:
            if link_id:
                add_link(
                    f,
                    link_type,
                    link_id,
                    label=labels.get(link_type),
                    actor_id=uploader_id,
                )
        for role_name, manage in sample.get("perms") or []:
            db.session.add(
                FilePermission(
                    file_id=f.id,
                    role_name=role_name,
                    can_view=True,
                    can_download=True,
                    can_manage=bool(manage),
                )
            )
        log_activity(f.id, "uploaded", f"Seeded {f.name}", uploader_id)
        created += 1

    db.session.commit()
    return created


# Back-compat helpers used by older templates
def files() -> list[dict]:
    return [serialize_file(f) for f in search_files()]


def get_file(file_id: int) -> dict | None:
    f = get_file_or_none(file_id)
    return serialize_file(f) if f else None


def versions_for(file_id: int) -> list[dict]:
    detail = build_detail_payload(file_id)
    return detail["versions"] if detail else []
