"""Helpdesk / ITSM services — tickets linked to infrastructure and files."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.assets import Asset
from uitop.models.helpdesk import (
    OBJECT_LINK_TYPES,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    TICKET_TYPES,
    Ticket,
    TicketActivity,
    TicketComment,
    TicketObjectLink,
    TicketTimeLog,
)
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User
from uitop.services.audit import log_audit
from uitop.services.computers_view import relative_time

SLA_HOURS = {
    "critical": 2,
    "high": 8,
    "medium": 24,
    "low": 72,
}

SLA_RESPONSE_MINUTES = {
    "critical": 15,
    "high": 60,
    "medium": 240,
    "low": 480,
}


def utcnow():
    return datetime.now(timezone.utc)


def next_ticket_number() -> str:
    last = Ticket.query.order_by(Ticket.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"HD-{2400 + n}"


def sla_due_for(priority: str, created_at: datetime | None = None) -> datetime:
    hours = SLA_HOURS.get(priority or "medium", 24)
    base = created_at or utcnow()
    return base + timedelta(hours=hours)


def get_ticket_or_404(ticket_id: int) -> Ticket:
    ticket = Ticket.query.get(ticket_id)
    if ticket is None:
        raise NotFoundError("Ticket not found")
    return ticket


def log_ticket_activity(
    ticket_id: int,
    activity_type: str,
    message: str | None = None,
    actor_id: int | None = None,
) -> None:
    db.session.add(
        TicketActivity(
            ticket_id=ticket_id,
            activity_type=activity_type,
            message=message,
            actor_user_id=actor_id,
        )
    )


def object_url(link_type: str, link_id: int) -> str | None:
    mapping = {
        "computer": f"/computers/{link_id}",
        "server": f"/servers/{link_id}",
        "network_device": f"/network/{link_id}",
        "printer": f"/printers/{link_id}",
        "asset": f"/assets/{link_id}",
    }
    return mapping.get(link_type)


def resolve_object_label(link_type: str, link_id: int, fallback: str | None = None) -> str:
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


def resolve_linked(ticket: Ticket):
    """Legacy primary device resolver."""
    if not ticket.linked_id or ticket.linked_type in (None, "none"):
        return None
    mapping = {
        "computer": Computer,
        "server": Server,
        "network_device": NetworkDevice,
        "printer": Printer,
    }
    model = mapping.get(ticket.linked_type)
    if not model:
        return None
    return model.query.get(ticket.linked_id)


def linked_summary(ticket: Ticket) -> dict | None:
    obj = resolve_linked(ticket)
    if obj is None:
        # Fall back to first object link
        link = ticket.object_links.order_by(TicketObjectLink.id.asc()).first()
        if not link:
            return None
        return {
            "type": link.link_type,
            "id": link.link_id,
            "label": link.label or resolve_object_label(link.link_type, link.link_id),
            "url": object_url(link.link_type, link.link_id),
        }
    if isinstance(obj, Computer):
        return {"type": "computer", "id": obj.id, "label": obj.hostname, "url": f"/computers/{obj.id}"}
    if isinstance(obj, Server):
        return {"type": "server", "id": obj.id, "label": obj.hostname, "url": f"/servers/{obj.id}"}
    if isinstance(obj, NetworkDevice):
        return {"type": "network_device", "id": obj.id, "label": obj.hostname, "url": f"/network/{obj.id}"}
    if isinstance(obj, Printer):
        return {"type": "printer", "id": obj.id, "label": obj.name, "url": f"/printers/{obj.id}"}
    return None


def serialize_object_link(link: TicketObjectLink) -> dict:
    label = link.label or resolve_object_label(link.link_type, link.link_id)
    return {
        "id": link.id,
        "type": link.link_type,
        "object_id": link.link_id,
        "label": label,
        "url": object_url(link.link_type, link.link_id),
        "type_label": link.link_type.replace("_", " ").title(),
    }


def device_snapshot(link_type: str, link_id: int) -> dict | None:
    """Lightweight live summary for Assets tab (infrastructure integration)."""
    if link_type == "computer":
        row = Computer.query.get(link_id)
        if not row:
            return None
        payload = row.inventory_payload or {}
        return {
            "type": "computer",
            "label": row.hostname,
            "url": f"/computers/{row.id}",
            "status": (row.status or "unknown").title(),
            "ip": row.ip_address,
            "os": row.os_name,
            "cpu": payload.get("cpu_percent") or payload.get("cpu"),
            "ram": payload.get("mem_percent") or payload.get("ram"),
            "disk": payload.get("disk_percent") or payload.get("disk"),
            "last_seen": relative_time(row.last_seen_at) if row.last_seen_at else "—",
            "agent": row.agent_version or "—",
        }
    if link_type == "server":
        row = Server.query.get(link_id)
        if not row:
            return None
        return {
            "type": "server",
            "label": row.hostname,
            "url": f"/servers/{row.id}",
            "status": (row.status or "unknown").title(),
            "ip": row.ip_address,
            "os": row.os_name,
            "role": row.role,
            "last_seen": relative_time(row.last_seen_at) if row.last_seen_at else "—",
            "agent": row.agent_version or "—",
        }
    if link_type == "printer":
        row = Printer.query.get(link_id)
        if not row:
            return None
        return {
            "type": "printer",
            "label": row.name,
            "url": f"/printers/{row.id}",
            "status": (row.status or "unknown").title(),
            "ip": row.ip_address,
            "model": row.model,
            "location": row.location,
        }
    if link_type == "network_device":
        row = NetworkDevice.query.get(link_id)
        if not row:
            return None
        return {
            "type": "network_device",
            "label": row.hostname,
            "url": f"/network/{row.id}",
            "status": (row.status or "unknown").title(),
            "ip": row.ip_address,
            "device_type": row.device_type,
            "vendor": row.vendor,
        }
    if link_type == "asset":
        row = Asset.query.get(link_id)
        if not row:
            return None
        return {
            "type": "asset",
            "label": row.asset_tag,
            "url": f"/assets/{row.id}",
            "status": (row.status or "").replace("_", " ").title(),
            "name": row.name,
            "serial": row.serial_number,
            "location": row.location,
        }
    return None


def is_sla_breached(ticket: Ticket) -> bool:
    if ticket.status in ("resolved", "closed"):
        return False
    if not ticket.sla_due_at:
        return False
    due = ticket.sla_due_at
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return utcnow() > due


def is_overdue(ticket: Ticket) -> bool:
    return is_sla_breached(ticket)


def serialize_ticket(ticket: Ticket) -> dict:
    data = ticket.to_dict()
    data["status_label"] = (ticket.status or "").replace("_", " ").title()
    data["priority_label"] = (ticket.priority or "").title()
    data["category_label"] = (ticket.category or "").replace("_", " ").title()
    data["type_label"] = (ticket.ticket_type or "incident").replace("_", " ").title()
    data["requester"] = (
        ticket.requester.full_name
        if ticket.requester
        else (ticket.requester_name or "—")
    )
    data["assignee"] = ticket.assignee.full_name if ticket.assignee else "Unassigned"
    data["department"] = ticket.department.name if ticket.department else "—"
    data["linked"] = linked_summary(ticket)
    data["object_links"] = [serialize_object_link(l) for l in ticket.object_links.all()]
    data["updated"] = relative_time(ticket.updated_at)
    data["created"] = relative_time(ticket.created_at)
    data["sla_breached"] = is_sla_breached(ticket)
    data["overdue"] = is_overdue(ticket)
    data["open"] = ticket.status not in ("resolved", "closed")
    data["problem_number"] = ticket.problem.ticket_number if ticket.problem else None
    data["related_incident_count"] = (
        ticket.related_incidents.count() if ticket.ticket_type == "problem" else 0
    )
    total_minutes = (
        db.session.query(func.coalesce(func.sum(TicketTimeLog.minutes), 0))
        .filter(TicketTimeLog.ticket_id == ticket.id)
        .scalar()
        or 0
    )
    data["time_logged_minutes"] = int(total_minutes)
    return data


def ticket_kpis(rows: list[dict] | None = None, *, assignee_user_id: int | None = None) -> dict:
    if rows is None:
        tickets = Ticket.query.all()
        rows = [serialize_ticket(t) for t in tickets]
    today = utcnow().date()
    open_count = sum(1 for r in rows if r["status"] not in ("resolved", "closed"))
    assigned_to_me = (
        sum(1 for r in rows if r.get("assignee_user_id") == assignee_user_id and r["open"])
        if assignee_user_id
        else 0
    )
    critical = sum(1 for r in rows if r.get("priority") == "critical" and r["open"])
    overdue = sum(1 for r in rows if r.get("overdue") or r.get("sla_breached"))
    resolved_today = 0
    resolution_minutes: list[float] = []
    for t in Ticket.query.all():
        if t.resolved_at:
            resolved = t.resolved_at
            if resolved.tzinfo is None:
                resolved = resolved.replace(tzinfo=timezone.utc)
            if resolved.date() == today:
                resolved_today += 1
            if t.created_at:
                cr = t.created_at
                if cr.tzinfo is None:
                    cr = cr.replace(tzinfo=timezone.utc)
                resolution_minutes.append((resolved - cr).total_seconds() / 60.0)
    avg_resolution = int(sum(resolution_minutes) / len(resolution_minutes)) if resolution_minutes else 0
    incidents = sum(1 for r in rows if r.get("ticket_type") == "incident" and r["open"])
    service_requests = sum(1 for r in rows if r.get("ticket_type") == "service_request" and r["open"])
    problems = sum(1 for r in rows if r.get("ticket_type") == "problem" and r["open"])
    return {
        "open": open_count,
        "assigned_to_me": assigned_to_me,
        "critical": critical,
        "overdue": overdue,
        "sla_breached": overdue,
        "resolved_today": resolved_today,
        "avg_resolution_min": avg_resolution,
        "avg_response_min": avg_resolution,  # back-compat for older templates
        "incidents": incidents,
        "service_requests": service_requests,
        "problems": problems,
        "total": len(rows),
    }


def status_mix() -> tuple[list[str], list[int]]:
    labels = ["Open", "In progress", "Pending", "Resolved", "Closed"]
    keys = ["open", "in_progress", "pending", "resolved", "closed"]
    values = [Ticket.query.filter_by(status=k).count() for k in keys]
    return labels, values


def list_tickets(
    *,
    status: str | None = None,
    ticket_type: str | None = None,
    priority: str | None = None,
    assignee_user_id: int | None = None,
    requester_user_id: int | None = None,
    department_id: int | None = None,
) -> list[dict]:
    q = Ticket.query.order_by(Ticket.updated_at.desc())
    if status:
        q = q.filter_by(status=status)
    if ticket_type:
        q = q.filter_by(ticket_type=ticket_type)
    if priority:
        q = q.filter_by(priority=priority)
    if assignee_user_id:
        q = q.filter_by(assignee_user_id=assignee_user_id)
    if requester_user_id:
        q = q.filter_by(requester_user_id=requester_user_id)
    if department_id:
        q = q.filter_by(department_id=department_id)
    return [serialize_ticket(t) for t in q.all()]


def add_object_link(
    ticket: Ticket,
    link_type: str,
    link_id: int,
    *,
    label: str | None = None,
    actor_id: int | None = None,
    commit: bool = False,
) -> TicketObjectLink | None:
    if link_type not in OBJECT_LINK_TYPES or not link_id:
        return None
    existing = TicketObjectLink.query.filter_by(
        ticket_id=ticket.id, link_type=link_type, link_id=link_id
    ).first()
    if existing:
        return existing
    resolved = resolve_object_label(link_type, link_id, label)
    link = TicketObjectLink(
        ticket_id=ticket.id,
        link_type=link_type,
        link_id=link_id,
        label=resolved,
    )
    db.session.add(link)
    # Keep legacy primary link if empty
    if ticket.linked_type in (None, "none") and link_type != "asset":
        ticket.linked_type = link_type
        ticket.linked_id = link_id
    if link_type == "asset" and not ticket.asset_id:
        ticket.asset_id = link_id
    log_ticket_activity(ticket.id, "linked", f"Linked {link_type}: {resolved}", actor_id)
    if commit:
        db.session.commit()
    return link


def create_ticket(
    *,
    subject: str,
    description: str | None = None,
    priority: str = "medium",
    category: str = "other",
    ticket_type: str = "incident",
    requester_user_id: int | None = None,
    requester_name: str | None = None,
    assignee_user_id: int | None = None,
    department_id: int | None = None,
    location: str | None = None,
    linked_type: str | None = None,
    linked_id: int | None = None,
    problem_id: int | None = None,
    actor_id: int | None = None,
) -> Ticket:
    subject = (subject or "").strip()
    if not subject:
        raise ValidationError("Subject is required")
    priority = (priority or "medium").lower()
    if priority not in TICKET_PRIORITIES:
        raise ValidationError("Invalid priority")
    category = (category or "other").lower()
    if category not in TICKET_CATEGORIES:
        raise ValidationError("Invalid category")
    ticket_type = (ticket_type or "incident").lower()
    if ticket_type not in TICKET_TYPES:
        raise ValidationError("Invalid ticket type")
    if not requester_user_id and not (requester_name or "").strip():
        raise ValidationError("Requester is required")
    if problem_id:
        parent = Ticket.query.get(problem_id)
        if parent is None or parent.ticket_type != "problem":
            raise ValidationError("Parent must be a Problem ticket")

    now = utcnow()
    ticket = Ticket(
        ticket_number=next_ticket_number(),
        subject=subject,
        description=(description or "").strip() or None,
        status="open",
        priority=priority,
        category=category,
        ticket_type=ticket_type,
        requester_user_id=requester_user_id,
        requester_name=(requester_name or "").strip() or None,
        assignee_user_id=assignee_user_id,
        department_id=department_id,
        created_by_id=actor_id,
        location=(location or "").strip() or None,
        linked_type=linked_type or "none",
        linked_id=linked_id,
        problem_id=problem_id,
        sla_due_at=sla_due_for(priority, now),
        created_at=now,
        updated_at=now,
    )
    db.session.add(ticket)
    db.session.flush()
    log_ticket_activity(ticket.id, "created", f"Ticket {ticket.ticket_number} created", actor_id)
    if linked_type and linked_type != "none" and linked_id:
        add_object_link(ticket, linked_type, linked_id, actor_id=actor_id)
    if assignee_user_id:
        log_ticket_activity(ticket.id, "assigned", "Assigned on create", actor_id)
        ticket.status = "in_progress"
        ticket.first_response_at = now
    db.session.commit()
    log_audit("helpdesk.create", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    try:
        from uitop.services import notifications as notif_svc

        notif_svc.notify_ticket_event(ticket, event="created", actor_id=actor_id)
        db.session.commit()
    except Exception:
        pass
    return ticket


def update_ticket(ticket_id: int, data: dict, actor_id: int | None = None) -> Ticket:
    ticket = get_ticket_or_404(ticket_id)
    if "subject" in data and data["subject"]:
        ticket.subject = data["subject"].strip()
    if "description" in data:
        ticket.description = (data["description"] or "").strip() or None
    if "priority" in data and data["priority"]:
        priority = data["priority"].lower()
        if priority not in TICKET_PRIORITIES:
            raise ValidationError("Invalid priority")
        if priority != ticket.priority:
            log_ticket_activity(
                ticket.id,
                "priority_changed",
                f"Priority {ticket.priority} → {priority}",
                actor_id,
            )
        ticket.priority = priority
        if ticket.status not in ("resolved", "closed"):
            ticket.sla_due_at = sla_due_for(priority, ticket.created_at)
    if "ticket_type" in data and data["ticket_type"]:
        ttype = data["ticket_type"].lower()
        if ttype not in TICKET_TYPES:
            raise ValidationError("Invalid ticket type")
        if ttype != ticket.ticket_type:
            log_ticket_activity(
                ticket.id,
                "type_changed",
                f"Type {ticket.ticket_type} → {ttype}",
                actor_id,
            )
        ticket.ticket_type = ttype
    if "category" in data and data["category"]:
        category = data["category"].lower()
        if category not in TICKET_CATEGORIES:
            raise ValidationError("Invalid category")
        ticket.category = category
    if "location" in data:
        ticket.location = (data["location"] or "").strip() or None
    if "department_id" in data:
        ticket.department_id = data["department_id"]
    if "requester_name" in data:
        ticket.requester_name = (data["requester_name"] or "").strip() or None
    if "requester_user_id" in data:
        ticket.requester_user_id = data["requester_user_id"]
    if "assignee_user_id" in data:
        ticket.assignee_user_id = data["assignee_user_id"]
    if "problem_id" in data:
        ticket.problem_id = data["problem_id"]
    if "linked_type" in data:
        ticket.linked_type = data["linked_type"] or "none"
    if "linked_id" in data:
        ticket.linked_id = data["linked_id"]
        if ticket.linked_type and ticket.linked_type != "none" and ticket.linked_id:
            add_object_link(ticket, ticket.linked_type, ticket.linked_id, actor_id=actor_id)
    if "status" in data and data["status"]:
        old_status = ticket.status
        _apply_status(ticket, data["status"].lower(), actor_id=actor_id)
        status_changed = old_status != ticket.status
    else:
        status_changed = False
    ticket.updated_at = utcnow()
    db.session.commit()
    log_audit("helpdesk.update", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    if status_changed:
        try:
            from uitop.services import notifications as notif_svc

            notif_svc.notify_ticket_event(ticket, event="status", actor_id=actor_id)
            db.session.commit()
        except Exception:
            pass
    return ticket


def _apply_status(ticket: Ticket, status: str, actor_id: int | None = None) -> None:
    if status not in TICKET_STATUSES:
        raise ValidationError("Invalid status")
    old = ticket.status
    ticket.status = status
    now = utcnow()
    if status == "resolved" and not ticket.resolved_at:
        ticket.resolved_at = now
        log_ticket_activity(ticket.id, "resolved", f"Status {old} → resolved", actor_id)
    elif status == "closed":
        if not ticket.resolved_at:
            ticket.resolved_at = now
        ticket.closed_at = now
        log_ticket_activity(ticket.id, "closed", f"Status {old} → closed", actor_id)
    elif status in ("open", "in_progress", "pending"):
        if old in ("resolved", "closed"):
            log_ticket_activity(ticket.id, "reopened", f"Status {old} → {status}", actor_id)
            ticket.resolved_at = None
            ticket.closed_at = None
        else:
            log_ticket_activity(ticket.id, "status_changed", f"Status {old} → {status}", actor_id)
    else:
        log_ticket_activity(ticket.id, "status_changed", f"Status {old} → {status}", actor_id)


def assign_ticket(ticket_id: int, assignee_user_id: int | None, actor_id: int | None = None) -> Ticket:
    ticket = get_ticket_or_404(ticket_id)
    if assignee_user_id:
        user = User.query.get(assignee_user_id)
        if user is None:
            raise ValidationError("Assignee not found")
        name = user.full_name
    else:
        name = "Unassigned"
    ticket.assignee_user_id = assignee_user_id
    if ticket.status == "open" and assignee_user_id:
        ticket.status = "in_progress"
    if not ticket.first_response_at and assignee_user_id:
        ticket.first_response_at = utcnow()
    ticket.updated_at = utcnow()
    log_ticket_activity(ticket.id, "assigned", f"Assigned to {name}", actor_id)
    db.session.commit()
    log_audit("helpdesk.assign", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    try:
        from uitop.services import notifications as notif_svc

        notif_svc.notify_ticket_event(ticket, event="assigned", actor_id=actor_id)
        db.session.commit()
    except Exception:
        pass
    return ticket


def add_comment(
    ticket_id: int,
    body: str,
    *,
    actor_id: int | None = None,
    is_internal: bool = False,
) -> TicketComment:
    ticket = get_ticket_or_404(ticket_id)
    body = (body or "").strip()
    if not body:
        raise ValidationError("Comment body is required")
    comment = TicketComment(
        ticket_id=ticket.id,
        author_user_id=actor_id,
        body=body,
        is_internal=bool(is_internal),
    )
    if not ticket.first_response_at:
        ticket.first_response_at = utcnow()
    if ticket.status == "open" and not is_internal:
        ticket.status = "in_progress"
    ticket.updated_at = utcnow()
    db.session.add(comment)
    log_ticket_activity(
        ticket.id,
        "commented",
        "Internal note added" if is_internal else "Comment added",
        actor_id,
    )
    db.session.commit()
    log_audit("helpdesk.comment", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    if not is_internal:
        try:
            from uitop.services import notifications as notif_svc

            notif_svc.notify_ticket_event(ticket, event="commented", actor_id=actor_id)
            db.session.commit()
        except Exception:
            pass
    return comment


def add_time_log(
    ticket_id: int,
    *,
    started_at: datetime | str,
    finished_at: datetime | str | None = None,
    minutes: int | None = None,
    note: str | None = None,
    actor_id: int | None = None,
) -> TicketTimeLog:
    ticket = get_ticket_or_404(ticket_id)

    def _parse(value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        # HTML datetime-local: 2026-07-24T09:30
        text = str(value).strip()
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        raise ValidationError("Invalid time format")

    start = _parse(started_at)
    if not start:
        raise ValidationError("Start time is required")
    end = _parse(finished_at)
    if minutes is None:
        if end:
            minutes = max(1, int((end - start).total_seconds() / 60))
        else:
            minutes = 0
    minutes = int(minutes or 0)
    if minutes < 0:
        raise ValidationError("Minutes cannot be negative")

    entry = TicketTimeLog(
        ticket_id=ticket.id,
        technician_user_id=actor_id,
        started_at=start,
        finished_at=end,
        minutes=minutes,
        note=(note or "").strip() or None,
    )
    db.session.add(entry)
    ticket.updated_at = utcnow()
    log_ticket_activity(ticket.id, "time_logged", f"Logged {minutes} minutes", actor_id)
    db.session.commit()
    return entry


def build_detail_payload(ticket_id: int) -> dict:
    ticket = get_ticket_or_404(ticket_id)
    comments = [
        c.to_dict()
        for c in TicketComment.query.filter_by(ticket_id=ticket.id)
        .order_by(TicketComment.created_at.asc())
        .all()
    ]
    links = [serialize_object_link(l) for l in ticket.object_links.all()]
    snapshots = []
    for link in links:
        snap = device_snapshot(link["type"], link["object_id"])
        if snap:
            snapshots.append(snap)
    time_logs = [t.to_dict() for t in ticket.time_logs.all()]
    activities = []
    for a in ticket.activities.limit(50).all():
        activities.append(
            {
                "type": a.activity_type,
                "message": a.message or a.activity_type.replace("_", " ").title(),
                "actor": a.actor.full_name if a.actor else "System",
                "when": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
            }
        )
    related = []
    if ticket.ticket_type == "problem":
        related = [serialize_ticket(t) for t in ticket.related_incidents.order_by(Ticket.id.desc()).all()]
    from uitop.services import files_view as files_svc

    files = files_svc.list_files_for_object("ticket", ticket.id)
    return {
        "ticket": serialize_ticket(ticket),
        "comments": comments,
        "object_links": links,
        "snapshots": snapshots,
        "time_logs": time_logs,
        "activities": activities,
        "related_incidents": related,
        "files": files,
        "sla_response_min": SLA_RESPONSE_MINUTES.get(ticket.priority or "medium", 240),
        "sla_resolve_hours": SLA_HOURS.get(ticket.priority or "medium", 24),
    }


def ensure_itsm_demo() -> int:
    """Upgrade thin ticket queues into a richer ITSM demo without wiping data."""
    from uitop.models.helpdesk import TicketActivity

    changed = 0
    # Backfill activity for tickets that predate TicketActivity
    for t in Ticket.query.all():
        if t.activities.count() == 0:
            log_ticket_activity(t.id, "created", f"Ticket {t.ticket_number} created", t.created_by_id)
            changed += 1
        if t.linked_type and t.linked_type != "none" and t.linked_id:
            if not TicketObjectLink.query.filter_by(
                ticket_id=t.id, link_type=t.linked_type, link_id=t.linked_id
            ).first():
                add_object_link(t, t.linked_type, t.linked_id, actor_id=t.created_by_id)
                changed += 1

    if not Ticket.query.filter_by(ticket_type="problem").count():
        admin = User.query.filter_by(is_super_admin=True).order_by(User.id.asc()).first()
        actor_id = admin.id if admin else None
        printer = Printer.query.order_by(Printer.id).first()
        problem = create_ticket(
            subject="HP LaserJet firmware failure — Finance wing",
            description="Root cause tracking for recurring Finance printer offline incidents.",
            priority="high",
            category="printer",
            ticket_type="problem",
            requester_name="IT Operations",
            location="Finance",
            actor_id=actor_id,
        )
        if printer:
            add_object_link(problem, "printer", printer.id, actor_id=actor_id, commit=True)
        # Tag an existing printer incident if present
        for t in Ticket.query.filter(Ticket.category == "printer", Ticket.ticket_type == "incident").all():
            t.problem_id = problem.id
            t.priority = "critical"
            changed += 1
        # Promote one software-ish ticket if subject matches install
        for t in Ticket.query.all():
            subj = (t.subject or "").lower()
            if "install" in subj or "mfa" in subj or "office" in subj:
                t.ticket_type = "service_request"
                changed += 1
        changed += 1

    if changed:
        db.session.commit()
    return changed


def seed_sample_tickets() -> int:
    """Create demo ITSM tickets if the queue is empty."""
    if Ticket.query.count():
        return 0
    admin = User.query.filter_by(is_super_admin=True).order_by(User.id.asc()).first()
    actor_id = admin.id if admin else None
    computer = Computer.query.order_by(Computer.id).first()
    printer = Printer.query.order_by(Printer.id).first()
    asset = Asset.query.order_by(Asset.id).first()

    problem = create_ticket(
        subject="HP LaserJet firmware failure — Finance wing",
        description="Root cause: intermittent offline state across Finance printers after firmware push.",
        priority="high",
        category="printer",
        ticket_type="problem",
        requester_name="IT Operations",
        location="Finance",
        actor_id=actor_id,
    )
    if printer:
        add_object_link(problem, "printer", printer.id, actor_id=actor_id, commit=True)

    samples = [
        {
            "subject": "VPN cannot connect from home",
            "description": "User reports FortiClient timeout after password prompt.",
            "priority": "high",
            "category": "vpn",
            "ticket_type": "incident",
            "requester_name": "K. Zulu",
            "location": "Remote / Dundee",
            "linked_type": "computer" if computer else "none",
            "linked_id": computer.id if computer else None,
        },
        {
            "subject": "Printer offline — Finance floor",
            "description": "HP LaserJet shows offline; users cannot print invoices.",
            "priority": "critical",
            "category": "printer",
            "ticket_type": "incident",
            "requester_name": "Finance Desk",
            "location": "Finance, 1st floor",
            "problem_id": problem.id,
            "linked_type": "printer" if printer else "none",
            "linked_id": printer.id if printer else None,
        },
        {
            "subject": "Install Microsoft Office",
            "description": "New starter needs Office suite and Teams.",
            "priority": "medium",
            "category": "software",
            "ticket_type": "service_request",
            "requester_name": "L. Mokoena",
            "location": "Corporate Services",
            "linked_type": "computer" if computer else "none",
            "linked_id": computer.id if computer else None,
        },
        {
            "subject": "Laptop slow boot after Windows update",
            "description": "Endpoint takes 8+ minutes to reach desktop.",
            "priority": "low",
            "category": "endpoint",
            "ticket_type": "incident",
            "requester_name": "S. Dlamini",
            "location": "Corporate Services",
            "linked_type": "computer" if computer else "none",
            "linked_id": computer.id if computer else None,
        },
        {
            "subject": "Reset MFA for organizational email",
            "description": "User lost phone; needs MFA reset for Exchange Online.",
            "priority": "high",
            "category": "account",
            "ticket_type": "service_request",
            "requester_name": "T. Nkosi",
            "location": "Technical Services",
        },
    ]
    created = 1  # problem already created
    for s in samples:
        linked_type = s.pop("linked_type", "none")
        linked_id = s.pop("linked_id", None)
        t = create_ticket(**s, linked_type=linked_type, linked_id=linked_id, actor_id=actor_id)
        if asset and t.category in ("endpoint", "printer"):
            add_object_link(t, "asset", asset.id, actor_id=actor_id, commit=True)
        created += 1

    tickets = Ticket.query.order_by(Ticket.id.asc()).all()
    if tickets and admin:
        assign_ticket(tickets[0].id, admin.id, actor_id=actor_id)
        # VPN ticket
        vpn = next((t for t in tickets if "VPN" in t.subject), None)
        if vpn:
            assign_ticket(vpn.id, admin.id, actor_id=actor_id)
            add_comment(vpn.id, "Checking FortiClient logs now.", actor_id=actor_id)
            add_time_log(
                vpn.id,
                started_at=utcnow() - timedelta(minutes=40),
                finished_at=utcnow(),
                note="VPN diagnostics",
                actor_id=actor_id,
            )
    pending = next((t for t in tickets if "slow boot" in t.subject.lower()), None)
    if pending:
        update_ticket(pending.id, {"status": "pending"}, actor_id=actor_id)
    return created
