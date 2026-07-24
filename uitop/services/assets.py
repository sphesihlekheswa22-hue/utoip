"""Asset lifecycle services — ownership layer over tech inventory."""
from __future__ import annotations

from uitop.core.errors import ConflictError, NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.assets import Asset, AssetAssignment, AssetCategory, AssetRequest, AssetVendor
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User
from uitop.services.audit import log_audit
from uitop.services.computers_view import relative_time


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def next_asset_tag() -> str:
    last = Asset.query.order_by(Asset.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"UMZ-AST-{10000 + n}"


def resolve_linked(asset: Asset):
    if not asset.linked_id or asset.linked_type in (None, "none"):
        return None
    mapping = {
        "computer": Computer,
        "server": Server,
        "network_device": NetworkDevice,
        "printer": Printer,
    }
    model = mapping.get(asset.linked_type)
    if not model:
        return None
    return model.query.get(asset.linked_id)


def linked_summary(asset: Asset) -> dict | None:
    obj = resolve_linked(asset)
    if obj is None:
        return None
    if isinstance(obj, Computer):
        return {
            "type": "computer",
            "id": obj.id,
            "label": obj.hostname,
            "url": f"/computers/{obj.id}",
            "status": obj.status,
            "ip": obj.ip_address,
        }
    if isinstance(obj, Server):
        return {
            "type": "server",
            "id": obj.id,
            "label": obj.hostname,
            "url": f"/servers/{obj.id}",
            "status": obj.status,
            "ip": obj.ip_address,
        }
    if isinstance(obj, NetworkDevice):
        return {
            "type": "network_device",
            "id": obj.id,
            "label": obj.hostname,
            "url": f"/network/{obj.id}",
            "status": obj.status,
            "ip": obj.ip_address,
        }
    if isinstance(obj, Printer):
        return {
            "type": "printer",
            "id": obj.id,
            "label": obj.name,
            "url": f"/printers/{obj.id}",
            "status": obj.status,
            "ip": obj.ip_address,
        }
    return None


def serialize_asset(asset: Asset) -> dict:
    data = asset.to_dict()
    data["status_label"] = (asset.status or "").replace("_", " ").title()
    data["linked"] = linked_summary(asset)
    data["updated"] = relative_time(asset.updated_at)
    active = (
        AssetAssignment.query.filter_by(asset_id=asset.id, returned_at=None)
        .order_by(AssetAssignment.assigned_at.desc())
        .first()
    )
    assignee = "—"
    if active:
        assignee = active.assignee_name or (active.user.full_name if active.user else "—")
    elif asset.custodian:
        assignee = asset.custodian.full_name
    data["assignee"] = assignee
    return data


def list_assets() -> list[dict]:
    rows = Asset.query.order_by(Asset.asset_tag.asc()).all()
    return [serialize_asset(a) for a in rows]


def asset_kpis(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "assigned": sum(1 for r in rows if r["status"] in {"assigned", "in_use"}),
        "in_store": sum(1 for r in rows if r["status"] == "in_store"),
        "in_repair": sum(1 for r in rows if r["status"] == "in_repair"),
        "linked": sum(1 for r in rows if r.get("linked")),
        "disposed": sum(1 for r in rows if r["status"] == "disposed"),
    }


def get_asset_or_404(asset_id: int) -> Asset:
    asset = Asset.query.get(asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_non_it_asset(
    *,
    name: str,
    category_id: int | None,
    location: str | None,
    serial_number: str | None,
    notes: str | None,
    actor_id: int | None,
    asset_tag: str | None = None,
) -> Asset:
    name = (name or "").strip()
    if not name:
        raise ValidationError("name is required")
    tag = (asset_tag or "").strip() or next_asset_tag()
    if Asset.query.filter_by(asset_tag=tag).first():
        raise ConflictError("Asset tag already exists")
    asset = Asset(
        asset_tag=tag,
        name=name,
        category_id=category_id,
        location=location,
        serial_number=serial_number,
        notes=notes,
        status="in_store",
        linked_type="none",
    )
    db.session.add(asset)
    db.session.commit()
    log_audit("assets.create", actor_user_id=actor_id, resource_type="asset", resource_id=asset.id)
    return asset


def link_asset_to_device(
    asset_id: int,
    *,
    linked_type: str,
    linked_id: int,
    actor_id: int | None = None,
) -> Asset:
    if linked_type not in {"computer", "server", "network_device", "printer"}:
        raise ValidationError("Invalid linked_type")
    asset = get_asset_or_404(asset_id)
    # Ensure target exists
    proxy = Asset(linked_type=linked_type, linked_id=linked_id)
    if resolve_linked(proxy) is None:
        raise NotFoundError("Linked device not found")
    # One asset per device
    existing = Asset.query.filter_by(linked_type=linked_type, linked_id=linked_id).first()
    if existing and existing.id != asset.id:
        raise ConflictError("Device already linked to another asset", details={"asset_id": existing.id})

    asset.linked_type = linked_type
    asset.linked_id = linked_id
    if asset.status == "in_store":
        asset.status = "in_use"
    db.session.commit()
    log_audit(
        "assets.link",
        actor_user_id=actor_id,
        resource_type="asset",
        resource_id=asset.id,
        meta={"linked_type": linked_type, "linked_id": linked_id},
    )
    return asset


def ensure_asset_for_computer(computer: Computer, actor_client_id: str | None = None) -> Asset:
    """Auto-create or update asset when a computer reports inventory."""
    existing = Asset.query.filter_by(linked_type="computer", linked_id=computer.id).first()
    if existing is None and computer.serial_number:
        existing = Asset.query.filter_by(serial_number=computer.serial_number).first()
        if existing and (existing.linked_type in (None, "none") or existing.linked_id is None):
            existing.linked_type = "computer"
            existing.linked_id = computer.id

    category = AssetCategory.query.filter_by(code="LAPTOP").first()
    if category is None:
        category = AssetCategory.query.filter_by(code="DESKTOP").first()
    hostname = computer.hostname or f"Computer-{computer.id}"
    name_parts = [p for p in [computer.manufacturer, computer.model] if p and p != "—"]
    name = " ".join(name_parts) if name_parts else hostname

    if existing is None:
        existing = Asset(
            asset_tag=computer.asset_tag or next_asset_tag(),
            name=name,
            serial_number=computer.serial_number,
            status="in_use",
            linked_type="computer",
            linked_id=computer.id,
            category_id=category.id if category else None,
            department_id=computer.department_id,
            location=None,
        )
        # Avoid unique tag clash
        if Asset.query.filter_by(asset_tag=existing.asset_tag).first():
            existing.asset_tag = next_asset_tag()
        db.session.add(existing)
        db.session.flush()
        log_audit(
            "assets.auto_create",
            actor_client_id=actor_client_id,
            resource_type="asset",
            resource_id=existing.id,
            meta={"computer_id": computer.id, "hostname": hostname},
        )
    else:
        existing.linked_type = "computer"
        existing.linked_id = computer.id
        if computer.serial_number:
            existing.serial_number = computer.serial_number
        if name and existing.name in (None, "", hostname):
            existing.name = name
        if existing.status in {"in_store", "ordered"}:
            existing.status = "in_use"
        db.session.flush()

    return existing


def assign_asset(
    asset_id: int,
    *,
    assignee_name: str | None,
    user_id: int | None,
    department_id: int | None,
    notes: str | None,
    actor_id: int | None,
) -> AssetAssignment:
    asset = get_asset_or_404(asset_id)
    # Close open assignment
    open_rows = AssetAssignment.query.filter_by(asset_id=asset.id, returned_at=None).all()
    now = utcnow()
    for row in open_rows:
        row.returned_at = now

    assignment = AssetAssignment(
        asset_id=asset.id,
        user_id=user_id,
        assignee_name=assignee_name,
        department_id=department_id,
        notes=notes,
        assigned_by_id=actor_id,
    )
    asset.status = "assigned"
    if user_id:
        asset.custodian_user_id = user_id
    if department_id:
        asset.department_id = department_id
    db.session.add(assignment)
    db.session.commit()
    log_audit(
        "assets.assign",
        actor_user_id=actor_id,
        resource_type="asset",
        resource_id=asset.id,
        meta={"assignee": assignee_name, "user_id": user_id},
    )
    return assignment


def create_request(
    *,
    requester_id: int,
    title: str,
    category_id: int | None,
    justification: str | None,
) -> AssetRequest:
    title = (title or "").strip()
    if not title:
        raise ValidationError("title is required")
    req = AssetRequest(
        requester_id=requester_id,
        category_id=category_id,
        title=title,
        justification=justification,
        status="pending",
    )
    db.session.add(req)
    db.session.commit()
    log_audit(
        "assets.request",
        actor_user_id=requester_id,
        resource_type="asset_request",
        resource_id=req.id,
    )
    return req


def seed_asset_catalog() -> dict:
    categories = [
        ("Laptop", "LAPTOP", True),
        ("Desktop", "DESKTOP", True),
        ("Monitor", "MONITOR", True),
        ("Server", "SERVER", True),
        ("Network", "NETWORK", True),
        ("Printer", "PRINTER", True),
        ("Mobile", "MOBILE", True),
        ("Peripheral", "PERIPH", True),
        ("Furniture", "FURN", False),
        ("Other", "OTHER", False),
    ]
    for name, code, is_it in categories:
        row = AssetCategory.query.filter_by(code=code).first()
        if row is None:
            db.session.add(AssetCategory(name=name, code=code, is_it=is_it))

    vendors = ["Dell", "HP", "Lenovo", "Cisco", "Brother", "Apple"]
    for name in vendors:
        if AssetVendor.query.filter_by(name=name).first() is None:
            db.session.add(AssetVendor(name=name))

    db.session.flush()
    return {
        "categories": AssetCategory.query.count(),
        "vendors": AssetVendor.query.count(),
    }


def seed_assets_from_inventory() -> int:
    """Link/create assets for existing computers/servers/network/printers."""
    created = 0
    laptop = AssetCategory.query.filter_by(code="LAPTOP").first()
    desktop = AssetCategory.query.filter_by(code="DESKTOP").first()
    server_cat = AssetCategory.query.filter_by(code="SERVER").first()
    network_cat = AssetCategory.query.filter_by(code="NETWORK").first()
    printer_cat = AssetCategory.query.filter_by(code="PRINTER").first()

    for computer in Computer.query.all():
        before = Asset.query.filter_by(linked_type="computer", linked_id=computer.id).first()
        ensure_asset_for_computer(computer)
        after = Asset.query.filter_by(linked_type="computer", linked_id=computer.id).first()
        if before is None and after is not None:
            created += 1
            # refine category
            if "lap" in (computer.hostname or "").lower() and laptop:
                after.category_id = laptop.id
            elif desktop:
                after.category_id = desktop.id

    for server in Server.query.all():
        if Asset.query.filter_by(linked_type="server", linked_id=server.id).first():
            continue
        asset = Asset(
            asset_tag=server.asset_tag or next_asset_tag(),
            name=server.hostname,
            status="in_use",
            linked_type="server",
            linked_id=server.id,
            category_id=server_cat.id if server_cat else None,
        )
        if Asset.query.filter_by(asset_tag=asset.asset_tag).first():
            asset.asset_tag = next_asset_tag()
        db.session.add(asset)
        created += 1

    for dev in NetworkDevice.query.all():
        if Asset.query.filter_by(linked_type="network_device", linked_id=dev.id).first():
            continue
        asset = Asset(
            asset_tag=next_asset_tag(),
            name=dev.hostname,
            status="in_use",
            linked_type="network_device",
            linked_id=dev.id,
            category_id=network_cat.id if network_cat else None,
            serial_number=dev.mac_address,
        )
        db.session.add(asset)
        created += 1

    for printer in Printer.query.all():
        if Asset.query.filter_by(linked_type="printer", linked_id=printer.id).first():
            continue
        asset = Asset(
            asset_tag=next_asset_tag(),
            name=printer.name,
            status="in_use" if (printer.status or "").lower() == "online" else "in_store",
            linked_type="printer",
            linked_id=printer.id,
            category_id=printer_cat.id if printer_cat else None,
            location=printer.location,
        )
        db.session.add(asset)
        created += 1

    # One non-IT example
    if not Asset.query.filter_by(asset_tag="UMZ-AST-FURN-01").first():
        furn = AssetCategory.query.filter_by(code="FURN").first()
        db.session.add(
            Asset(
                asset_tag="UMZ-AST-FURN-01",
                name="Meeting room table set",
                status="in_store",
                category_id=furn.id if furn else None,
                location="Stores",
                linked_type="none",
                notes="Non-IT asset example — no agent link",
            )
        )
        created += 1

    db.session.flush()
    return created
