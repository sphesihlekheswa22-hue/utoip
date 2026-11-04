"""Maintenance work-order services — preventive & corrective IT ops."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.assets import Asset
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.maintenance import (
    ASSET_LINK_TYPES,
    PLAN_FREQUENCIES,
    WO_PRIORITIES,
    WO_STATUSES,
    WO_TYPES,
    MaintenanceActivity,
    MaintenanceChecklistItem,
    MaintenancePart,
    MaintenancePlan,
    MaintenanceWorkOrder,
)
from uitop.models.user import User
from uitop.services.audit import log_audit
from uitop.services.computers_view import relative_time


def utcnow():
    return datetime.now(timezone.utc)


def next_wo_number() -> str:
    last = MaintenanceWorkOrder.query.order_by(MaintenanceWorkOrder.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"WO-{12000 + n}"


def get_wo_or_404(wo_id: int) -> MaintenanceWorkOrder:
    row = MaintenanceWorkOrder.query.get(wo_id)
    if row is None:
        raise NotFoundError("Work order not found")
    return row


def log_activity(wo_id: int, activity_type: str, message: str | None = None, actor_id: int | None = None) -> None:
    db.session.add(
        MaintenanceActivity(
            work_order_id=wo_id,
            activity_type=activity_type,
            message=message,
            actor_user_id=actor_id,
        )
    )


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
    return f"{link_type} #{link_id}"


def link_url(link_type: str, link_id: int | None) -> str | None:
    if not link_id:
        return None
    mapping = {
        "computer": f"/computers/{link_id}",
        "server": f"/servers/{link_id}",
        "network_device": f"/network/{link_id}",
        "printer": f"/printers/{link_id}",
        "asset": f"/assets/{link_id}",
    }
    return mapping.get(link_type)


def asset_snapshot(wo: MaintenanceWorkOrder) -> dict | None:
    if wo.linked_type == "server" and wo.linked_id:
        row = Server.query.get(wo.linked_id)
        if row:
            return {
                "type": "Server",
                "label": row.hostname,
                "url": f"/servers/{row.id}",
                "status": (row.status or "unknown").title(),
                "ip": row.ip_address,
                "meta": row.role or row.os_name or "—",
                "location": wo.location or "—",
            }
    if wo.linked_type == "computer" and wo.linked_id:
        row = Computer.query.get(wo.linked_id)
        if row:
            return {
                "type": "Computer",
                "label": row.hostname,
                "url": f"/computers/{row.id}",
                "status": (row.status or "unknown").title(),
                "ip": row.ip_address,
                "meta": f"{row.manufacturer or ''} {row.model or ''}".strip() or row.os_name or "—",
                "location": wo.location or "—",
            }
    if wo.linked_type == "printer" and wo.linked_id:
        row = Printer.query.get(wo.linked_id)
        if row:
            return {
                "type": "Printer",
                "label": row.name,
                "url": f"/printers/{row.id}",
                "status": (row.status or "unknown").title(),
                "ip": row.ip_address,
                "meta": row.model or "—",
                "location": row.location or wo.location or "—",
            }
    if wo.linked_type == "network_device" and wo.linked_id:
        row = NetworkDevice.query.get(wo.linked_id)
        if row:
            return {
                "type": "Network",
                "label": row.hostname,
                "url": f"/network/{row.id}",
                "status": (row.status or "unknown").title(),
                "ip": row.ip_address,
                "meta": f"{row.vendor or ''} {row.device_type or ''}".strip() or "—",
                "location": wo.location or "—",
            }
    if wo.asset_id or (wo.linked_type == "asset" and wo.linked_id):
        aid = wo.asset_id or wo.linked_id
        row = Asset.query.get(aid)
        if row:
            return {
                "type": "Asset",
                "label": row.asset_tag,
                "url": f"/assets/{row.id}",
                "status": (row.status or "").replace("_", " ").title(),
                "ip": None,
                "meta": row.name,
                "location": row.location or wo.location or "—",
                "warranty": "Active" if row.warranty_expires and row.warranty_expires >= utcnow().date() else "—",
            }
    if wo.linked_label:
        return {
            "type": (wo.linked_type or "asset").replace("_", " ").title(),
            "label": wo.linked_label,
            "url": link_url(wo.linked_type, wo.linked_id),
            "status": "—",
            "ip": None,
            "meta": "—",
            "location": wo.location or "—",
        }
    return None


def is_overdue(wo: MaintenanceWorkOrder) -> bool:
    if wo.status in ("completed", "cancelled"):
        return False
    due = wo.due_at or wo.scheduled_at
    if not due:
        return False
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return utcnow() > due


def serialize_wo(wo: MaintenanceWorkOrder) -> dict:
    data = wo.to_dict()
    data["type_label"] = (wo.maintenance_type or "").title()
    data["status_label"] = (wo.status or "").replace("_", " ").title()
    data["priority_label"] = (wo.priority or "").title()
    data["technician"] = wo.technician.full_name if wo.technician else "Unassigned"
    data["vendor"] = wo.vendor.name if wo.vendor else "—"
    data["asset_label"] = wo.linked_label or resolve_link_label(wo.linked_type, wo.linked_id or 0)
    data["asset_url"] = link_url(wo.linked_type, wo.linked_id)
    data["overdue"] = is_overdue(wo)
    data["scheduled"] = relative_time(wo.scheduled_at) if wo.scheduled_at else "—"
    data["due"] = relative_time(wo.due_at) if wo.due_at else (data["scheduled"] if wo.scheduled_at else "—")
    data["completed"] = relative_time(wo.completed_at) if wo.completed_at else "—"
    data["updated"] = relative_time(wo.updated_at)
    data["checklist_done"] = wo.checklist_items.filter_by(is_done=True).count()
    data["checklist_total"] = wo.checklist_items.count()
    return data


def maintenance_kpis() -> dict:
    rows = MaintenanceWorkOrder.query.all()
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    scheduled = sum(1 for w in rows if w.status == "scheduled")
    in_progress = sum(1 for w in rows if w.status == "in_progress")
    completed_month = sum(
        1
        for w in rows
        if w.status == "completed"
        and w.completed_at
        and (w.completed_at if w.completed_at.tzinfo else w.completed_at.replace(tzinfo=timezone.utc)) >= month_start
    )
    overdue = sum(1 for w in rows if is_overdue(w))
    preventive = sum(1 for w in rows if w.maintenance_type == "preventive")
    corrective = sum(1 for w in rows if w.maintenance_type == "corrective")
    emergency = sum(1 for w in rows if w.maintenance_type == "emergency")
    return {
        "scheduled": scheduled,
        "in_progress": in_progress,
        "completed_month": completed_month,
        "overdue": overdue,
        "preventive": preventive,
        "corrective": corrective,
        "emergency": emergency,
        "total": len(rows),
        "plans": MaintenancePlan.query.filter_by(is_active=True).count(),
    }


def list_work_orders(
    *,
    status: str | None = None,
    maintenance_type: str | None = None,
    view: str | None = None,
) -> list[dict]:
    q = MaintenanceWorkOrder.query.order_by(MaintenanceWorkOrder.updated_at.desc())
    if status:
        q = q.filter_by(status=status)
    if maintenance_type:
        q = q.filter_by(maintenance_type=maintenance_type)
    rows = [serialize_wo(w) for w in q.all()]
    if view == "scheduled":
        rows = [r for r in rows if r["status"] == "scheduled"]
    elif view == "completed":
        rows = [r for r in rows if r["status"] == "completed"]
    elif view == "overdue":
        rows = [r for r in rows if r["overdue"]]
    elif view == "work_orders":
        rows = [r for r in rows if r["status"] not in ("completed", "cancelled")]
    return rows


def create_work_order(
    *,
    title: str,
    description: str | None = None,
    maintenance_type: str = "preventive",
    priority: str = "medium",
    linked_type: str = "asset",
    linked_id: int | None = None,
    linked_label: str | None = None,
    asset_id: int | None = None,
    technician_user_id: int | None = None,
    vendor_id: int | None = None,
    ticket_id: int | None = None,
    plan_id: int | None = None,
    location: str | None = None,
    scheduled_at: datetime | str | None = None,
    due_at: datetime | str | None = None,
    checklist: list[str] | None = None,
    actor_id: int | None = None,
) -> MaintenanceWorkOrder:
    title = (title or "").strip()
    if not title:
        raise ValidationError("Title is required")
    maintenance_type = (maintenance_type or "preventive").lower()
    if maintenance_type not in WO_TYPES:
        raise ValidationError("Invalid maintenance type")
    priority = (priority or "medium").lower()
    if priority not in WO_PRIORITIES:
        raise ValidationError("Invalid priority")
    linked_type = linked_type or "asset"
    if linked_type not in ASSET_LINK_TYPES:
        raise ValidationError("Invalid linked object type")

    def _parse(value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip().replace("Z", "")
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                sample = text[:16] if "T" in text or " " in text else text[:10]
                if fmt == "%Y-%m-%d":
                    sample = text[:10]
                return datetime.strptime(sample, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    sched = _parse(scheduled_at) or utcnow() + timedelta(days=1)
    due = _parse(due_at) or sched
    label = resolve_link_label(linked_type, linked_id or 0, linked_label) if linked_id else linked_label

    wo = MaintenanceWorkOrder(
        work_order_number=next_wo_number(),
        title=title,
        description=(description or "").strip() or None,
        maintenance_type=maintenance_type,
        status="scheduled",
        priority=priority,
        linked_type=linked_type,
        linked_id=linked_id,
        linked_label=label,
        asset_id=asset_id or (linked_id if linked_type == "asset" else None),
        technician_user_id=technician_user_id,
        vendor_id=vendor_id,
        ticket_id=ticket_id,
        plan_id=plan_id,
        created_by_id=actor_id,
        location=(location or "").strip() or None,
        scheduled_at=sched,
        due_at=due,
    )
    db.session.add(wo)
    db.session.flush()
    for i, item in enumerate(checklist or []):
        text = (item or "").strip()
        if text:
            db.session.add(
                MaintenanceChecklistItem(work_order_id=wo.id, label=text, sort_order=i, is_done=False)
            )
    log_activity(wo.id, "created", f"Work order {wo.work_order_number} created", actor_id)
    if technician_user_id:
        log_activity(wo.id, "assigned", "Technician assigned", actor_id)
    db.session.commit()
    log_audit("maintenance.create", actor_user_id=actor_id, resource_type="work_order", resource_id=wo.id)
    return wo


def update_work_order(wo_id: int, data: dict, actor_id: int | None = None) -> MaintenanceWorkOrder:
    wo = get_wo_or_404(wo_id)
    if "title" in data and data["title"]:
        wo.title = data["title"].strip()
    if "description" in data:
        wo.description = (data["description"] or "").strip() or None
    if "priority" in data and data["priority"]:
        p = data["priority"].lower()
        if p not in WO_PRIORITIES:
            raise ValidationError("Invalid priority")
        wo.priority = p
    if "maintenance_type" in data and data["maintenance_type"]:
        t = data["maintenance_type"].lower()
        if t not in WO_TYPES:
            raise ValidationError("Invalid type")
        wo.maintenance_type = t
    if "technician_user_id" in data:
        wo.technician_user_id = data["technician_user_id"]
        log_activity(wo.id, "assigned", "Technician updated", actor_id)
    if "location" in data:
        wo.location = (data["location"] or "").strip() or None
    if "labour_cost" in data and data["labour_cost"] is not None:
        wo.labour_cost = float(data["labour_cost"] or 0)
    if "travel_cost" in data and data["travel_cost"] is not None:
        wo.travel_cost = float(data["travel_cost"] or 0)
    if "other_cost" in data and data["other_cost"] is not None:
        wo.other_cost = float(data["other_cost"] or 0)
    if "status" in data and data["status"]:
        _apply_status(wo, data["status"].lower(), actor_id=actor_id)
    wo.updated_at = utcnow()
    db.session.commit()
    return wo


def _apply_status(wo: MaintenanceWorkOrder, status: str, actor_id: int | None = None) -> None:
    if status not in WO_STATUSES:
        raise ValidationError("Invalid status")
    old = wo.status
    wo.status = status
    now = utcnow()
    if status == "in_progress" and not wo.started_at:
        wo.started_at = now
        log_activity(wo.id, "started", f"Status {old} → in progress", actor_id)
    elif status == "completed":
        wo.completed_at = now
        if not wo.started_at:
            wo.started_at = now
        log_activity(wo.id, "completed", f"Status {old} → completed", actor_id)
    else:
        log_activity(wo.id, "status_changed", f"Status {old} → {status}", actor_id)


def toggle_checklist(item_id: int, actor_id: int | None = None) -> MaintenanceChecklistItem:
    item = MaintenanceChecklistItem.query.get(item_id)
    if item is None:
        raise NotFoundError("Checklist item not found")
    item.is_done = not item.is_done
    item.completed_at = utcnow() if item.is_done else None
    log_activity(
        item.work_order_id,
        "checklist",
        f"{'Checked' if item.is_done else 'Unchecked'}: {item.label}",
        actor_id,
    )
    item.work_order.updated_at = utcnow()
    db.session.commit()
    return item


def add_part(
    wo_id: int,
    *,
    part_name: str,
    quantity: int = 1,
    unit_cost: float = 0,
    notes: str | None = None,
    actor_id: int | None = None,
) -> MaintenancePart:
    wo = get_wo_or_404(wo_id)
    part_name = (part_name or "").strip()
    if not part_name:
        raise ValidationError("Part name is required")
    part = MaintenancePart(
        work_order_id=wo.id,
        part_name=part_name,
        quantity=max(1, int(quantity or 1)),
        unit_cost=float(unit_cost or 0),
        notes=(notes or "").strip() or None,
    )
    db.session.add(part)
    # Recalc parts cost
    db.session.flush()
    wo.parts_cost = sum(p.line_total for p in wo.parts.all())
    log_activity(wo.id, "parts", f"Added part {part_name} ×{part.quantity}", actor_id)
    wo.updated_at = utcnow()
    db.session.commit()
    return part


def build_detail_payload(wo_id: int) -> dict:
    wo = get_wo_or_404(wo_id)
    checklist = [
        {
            "id": c.id,
            "label": c.label,
            "is_done": c.is_done,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        }
        for c in wo.checklist_items.all()
    ]
    parts = [
        {
            "id": p.id,
            "name": p.part_name,
            "quantity": p.quantity,
            "unit_cost": p.unit_cost,
            "line_total": p.line_total,
            "notes": p.notes,
        }
        for p in wo.parts.all()
    ]
    activities = [
        {
            "type": a.activity_type,
            "message": a.message or a.activity_type.replace("_", " ").title(),
            "actor": a.actor.full_name if a.actor else "System",
            "when": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        }
        for a in wo.activities.limit(50).all()
    ]
    from uitop.services import files_view as files_svc

    files = files_svc.list_files_for_object("maintenance", wo.id)
    ai_insights = []
    if wo.maintenance_type == "corrective":
        ai_insights.append(
            {
                "title": "Repeat failure risk",
                "body": "If this asset has multiple corrective work orders this year, consider replacement vs repair.",
                "tone": "warning",
            }
        )
    if is_overdue(wo):
        ai_insights.append(
            {
                "title": "Overdue maintenance",
                "body": "This work order is past due — prioritize to reduce outage risk.",
                "tone": "danger",
            }
        )
    return {
        "work_order": serialize_wo(wo),
        "checklist": checklist,
        "parts": parts,
        "activities": activities,
        "asset": asset_snapshot(wo),
        "files": files,
        "ai_insights": ai_insights,
        "costs": {
            "labour": wo.labour_cost or 0,
            "parts": wo.parts_cost or 0,
            "travel": wo.travel_cost or 0,
            "other": wo.other_cost or 0,
            "total": wo.total_cost,
        },
    }


def list_plans() -> list[dict]:
    return [p.to_dict() for p in MaintenancePlan.query.order_by(MaintenancePlan.name).all()]


def create_plan(
    *,
    name: str,
    description: str | None = None,
    frequency: str = "monthly",
    interval_days: int | None = None,
    linked_type: str | None = None,
    checklist: list[str] | None = None,
    actor_id: int | None = None,
) -> MaintenancePlan:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Plan name is required")
    frequency = (frequency or "monthly").lower()
    if frequency not in PLAN_FREQUENCIES:
        raise ValidationError("Invalid frequency")
    days_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
    days = interval_days or days_map.get(frequency, 30)
    plan = MaintenancePlan(
        name=name,
        description=(description or "").strip() or None,
        maintenance_type="preventive",
        frequency=frequency,
        interval_days=int(days),
        linked_type=linked_type,
        checklist_template=checklist or [],
        is_active=True,
        next_run_at=utcnow() + timedelta(days=int(days)),
    )
    db.session.add(plan)
    db.session.commit()
    log_audit("maintenance.plan_create", actor_user_id=actor_id, resource_type="maintenance_plan", resource_id=plan.id)
    return plan


def seed_sample_maintenance(*, actor_id: int | None = None) -> int:
    if MaintenanceWorkOrder.query.count():
        return 0
    admin = User.query.filter_by(email="admin@umzinyathi.gov.za").first()
    actor_id = actor_id or (admin.id if admin else None)
    server = Server.query.order_by(Server.id).first()
    computer = Computer.query.order_by(Computer.id).first()
    printer = Printer.query.order_by(Printer.id).first()
    asset = Asset.query.order_by(Asset.id).first()

    plan = create_plan(
        name="Monthly Server Inspection",
        description="Dust, firmware, disk health, backup verification.",
        frequency="monthly",
        linked_type="server",
        checklist=[
            "Dust cleaned",
            "Firmware updated",
            "Disk health checked",
            "Backup verified",
            "UPS battery checked",
        ],
        actor_id=actor_id,
    )
    create_plan(
        name="Quarterly Switch Review",
        description="Port status, firmware, config backup.",
        frequency="quarterly",
        linked_type="network_device",
        checklist=["Config backed up", "Firmware reviewed", "Port errors checked"],
        actor_id=actor_id,
    )
    create_plan(
        name="Printer Servicing (6 months)",
        description="Clean path, rollers, firmware.",
        frequency="custom_days",
        interval_days=180,
        linked_type="printer",
        checklist=["Paper path cleaned", "Firmware updated", "Test page printed"],
        actor_id=actor_id,
    )

    samples = [
        {
            "title": "Server inspection — primary app host",
            "maintenance_type": "preventive",
            "priority": "high",
            "linked_type": "server",
            "linked_id": server.id if server else None,
            "location": "Server Room",
            "plan_id": plan.id,
            "checklist": plan.checklist_template,
            "scheduled_at": utcnow() + timedelta(days=1),
        },
        {
            "title": "Replace failing SSD",
            "description": "Disk health alert from Monitoring — corrective replacement.",
            "maintenance_type": "corrective",
            "priority": "critical",
            "linked_type": "server",
            "linked_id": server.id if server else None,
            "location": "Server Room",
            "checklist": ["Backup verified", "SSD replaced", "Diagnostics passed", "Monitoring cleared"],
            "scheduled_at": utcnow() - timedelta(hours=2),
        },
        {
            "title": "Finance printer servicing",
            "maintenance_type": "preventive",
            "priority": "medium",
            "linked_type": "printer",
            "linked_id": printer.id if printer else None,
            "location": "Finance Wing",
            "checklist": ["Paper path cleaned", "Firmware updated", "Test page printed"],
            "scheduled_at": utcnow() + timedelta(days=5),
        },
        {
            "title": "Endpoint dust clean & thermal check",
            "maintenance_type": "preventive",
            "priority": "low",
            "linked_type": "computer",
            "linked_id": computer.id if computer else None,
            "location": "Corporate Services",
            "checklist": ["Dust cleaned", "Thermal paste OK", "Windows updates applied"],
            "scheduled_at": utcnow() - timedelta(days=3),
        },
        {
            "title": "UPS battery replacement",
            "maintenance_type": "corrective",
            "priority": "high",
            "linked_type": "asset",
            "linked_id": asset.id if asset else None,
            "location": "Server Room",
            "checklist": ["Old battery removed", "New battery installed", "Runtime test passed"],
            "scheduled_at": utcnow() + timedelta(days=2),
        },
    ]

    created = 0
    for s in samples:
        linked_id = s.pop("linked_id", None)
        checklist = s.pop("checklist", None)
        wo = create_work_order(
            **s,
            linked_id=linked_id,
            checklist=checklist,
            technician_user_id=actor_id,
            actor_id=actor_id,
        )
        created += 1
        if "SSD" in wo.title:
            update_work_order(wo.id, {"status": "in_progress", "labour_cost": 850, "travel_cost": 150}, actor_id=actor_id)
            add_part(wo.id, part_name="SSD 1TB", quantity=1, unit_cost=2100, actor_id=actor_id)
            add_part(wo.id, part_name="RAM 16GB", quantity=2, unit_cost=900, actor_id=actor_id)
        if "dust clean" in wo.title.lower():
            update_work_order(wo.id, {"status": "completed", "labour_cost": 350}, actor_id=actor_id)
            for item in wo.checklist_items.all():
                item.is_done = True
                item.completed_at = utcnow()
            db.session.commit()

    return created
