"""Helpdesk ticket services."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.helpdesk import (
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    Ticket,
    TicketComment,
)
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User
from uitop.services.audit import log_audit
from uitop.services.computers_view import relative_time

SLA_HOURS = {
    "critical": 4,
    "high": 8,
    "medium": 24,
    "low": 72,
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


def resolve_linked(ticket: Ticket):
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
        return None
    if isinstance(obj, Computer):
        return {"type": "computer", "id": obj.id, "label": obj.hostname, "url": f"/computers/{obj.id}"}
    if isinstance(obj, Server):
        return {"type": "server", "id": obj.id, "label": obj.hostname, "url": f"/servers/{obj.id}"}
    if isinstance(obj, NetworkDevice):
        return {"type": "network_device", "id": obj.id, "label": obj.hostname, "url": f"/network/{obj.id}"}
    if isinstance(obj, Printer):
        return {"type": "printer", "id": obj.id, "label": obj.name, "url": f"/printers/{obj.id}"}
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


def serialize_ticket(ticket: Ticket) -> dict:
    data = ticket.to_dict()
    data["status_label"] = (ticket.status or "").replace("_", " ").title()
    data["priority_label"] = (ticket.priority or "").title()
    data["category_label"] = (ticket.category or "").replace("_", " ").title()
    data["requester"] = (
        ticket.requester.full_name
        if ticket.requester
        else (ticket.requester_name or "—")
    )
    data["assignee"] = ticket.assignee.full_name if ticket.assignee else "Unassigned"
    data["department"] = ticket.department.name if ticket.department else "—"
    data["linked"] = linked_summary(ticket)
    data["updated"] = relative_time(ticket.updated_at)
    data["created"] = relative_time(ticket.created_at)
    data["sla_breached"] = is_sla_breached(ticket)
    data["open"] = ticket.status not in ("resolved", "closed")
    return data


def ticket_kpis(rows: list[dict] | None = None) -> dict:
    if rows is None:
        tickets = Ticket.query.all()
        rows = [serialize_ticket(t) for t in tickets]
    today = utcnow().date()
    open_count = sum(1 for r in rows if r["status"] not in ("resolved", "closed"))
    breached = sum(1 for r in rows if r.get("sla_breached"))
    resolved_today = 0
    response_minutes: list[float] = []
    for t in Ticket.query.all():
        if t.resolved_at:
            resolved = t.resolved_at
            if resolved.tzinfo is None:
                resolved = resolved.replace(tzinfo=timezone.utc)
            if resolved.date() == today:
                resolved_today += 1
        if t.first_response_at and t.created_at:
            fr = t.first_response_at
            cr = t.created_at
            if fr.tzinfo is None:
                fr = fr.replace(tzinfo=timezone.utc)
            if cr.tzinfo is None:
                cr = cr.replace(tzinfo=timezone.utc)
            response_minutes.append((fr - cr).total_seconds() / 60.0)
    avg_response = int(sum(response_minutes) / len(response_minutes)) if response_minutes else 0
    return {
        "open": open_count,
        "sla_breached": breached,
        "resolved_today": resolved_today,
        "avg_response_min": avg_response,
        "total": len(rows),
    }


def status_mix() -> tuple[list[str], list[int]]:
    labels = ["Open", "In progress", "Pending", "Resolved", "Closed"]
    keys = ["open", "in_progress", "pending", "resolved", "closed"]
    values = [Ticket.query.filter_by(status=k).count() for k in keys]
    return labels, values


def list_tickets(*, status: str | None = None) -> list[dict]:
    q = Ticket.query.order_by(Ticket.updated_at.desc())
    if status:
        q = q.filter_by(status=status)
    return [serialize_ticket(t) for t in q.all()]


def create_ticket(
    *,
    subject: str,
    description: str | None = None,
    priority: str = "medium",
    category: str = "other",
    requester_user_id: int | None = None,
    requester_name: str | None = None,
    assignee_user_id: int | None = None,
    department_id: int | None = None,
    location: str | None = None,
    linked_type: str | None = None,
    linked_id: int | None = None,
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
    if not requester_user_id and not (requester_name or "").strip():
        raise ValidationError("Requester is required")

    now = utcnow()
    ticket = Ticket(
        ticket_number=next_ticket_number(),
        subject=subject,
        description=(description or "").strip() or None,
        status="open",
        priority=priority,
        category=category,
        requester_user_id=requester_user_id,
        requester_name=(requester_name or "").strip() or None,
        assignee_user_id=assignee_user_id,
        department_id=department_id,
        created_by_id=actor_id,
        location=(location or "").strip() or None,
        linked_type=linked_type or "none",
        linked_id=linked_id,
        sla_due_at=sla_due_for(priority, now),
        created_at=now,
        updated_at=now,
    )
    db.session.add(ticket)
    db.session.commit()
    log_audit("helpdesk.create", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
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
        ticket.priority = priority
        if ticket.status not in ("resolved", "closed"):
            ticket.sla_due_at = sla_due_for(priority, ticket.created_at)
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
    if "linked_type" in data:
        ticket.linked_type = data["linked_type"] or "none"
    if "linked_id" in data:
        ticket.linked_id = data["linked_id"]
    if "status" in data and data["status"]:
        _apply_status(ticket, data["status"].lower())
    ticket.updated_at = utcnow()
    db.session.commit()
    log_audit("helpdesk.update", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    return ticket


def _apply_status(ticket: Ticket, status: str) -> None:
    if status not in TICKET_STATUSES:
        raise ValidationError("Invalid status")
    ticket.status = status
    now = utcnow()
    if status == "resolved" and not ticket.resolved_at:
        ticket.resolved_at = now
    if status == "closed":
        if not ticket.resolved_at:
            ticket.resolved_at = now
        ticket.closed_at = now
    if status in ("open", "in_progress", "pending"):
        ticket.resolved_at = None
        ticket.closed_at = None


def assign_ticket(ticket_id: int, assignee_user_id: int | None, actor_id: int | None = None) -> Ticket:
    ticket = get_ticket_or_404(ticket_id)
    if assignee_user_id:
        user = User.query.get(assignee_user_id)
        if user is None:
            raise ValidationError("Assignee not found")
    ticket.assignee_user_id = assignee_user_id
    if ticket.status == "open" and assignee_user_id:
        ticket.status = "in_progress"
    if not ticket.first_response_at and assignee_user_id:
        ticket.first_response_at = utcnow()
    ticket.updated_at = utcnow()
    db.session.commit()
    log_audit("helpdesk.assign", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
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
    db.session.commit()
    log_audit("helpdesk.comment", actor_user_id=actor_id, resource_type="ticket", resource_id=ticket.id)
    return comment


def seed_sample_tickets() -> int:
    """Create a few demo tickets if the queue is empty."""
    if Ticket.query.count():
        return 0
    admin = User.query.filter_by(email="admin@umzinyathi.gov.za").first()
    actor_id = admin.id if admin else None
    samples = [
        {
            "subject": "VPN cannot connect from home",
            "description": "User reports FortiClient timeout after password prompt.",
            "priority": "high",
            "category": "vpn",
            "requester_name": "K. Zulu",
            "location": "Remote / Dundee",
        },
        {
            "subject": "Printer jam — Finance floor",
            "description": "HP LaserJet on Finance wing keeps jamming on duplex jobs.",
            "priority": "medium",
            "category": "printer",
            "requester_name": "Finance Desk",
            "location": "Finance, 1st floor",
        },
        {
            "subject": "Laptop slow boot after Windows update",
            "description": "Endpoint takes 8+ minutes to reach desktop.",
            "priority": "low",
            "category": "endpoint",
            "requester_name": "L. Mokoena",
            "location": "Corporate Services",
        },
    ]
    created = 0
    for s in samples:
        create_ticket(**s, actor_id=actor_id)
        created += 1
    # Assign first to admin and mark second pending
    tickets = Ticket.query.order_by(Ticket.id.asc()).all()
    if tickets and admin:
        assign_ticket(tickets[0].id, admin.id, actor_id=actor_id)
    if len(tickets) > 1:
        update_ticket(tickets[1].id, {"status": "pending"}, actor_id=actor_id)
    return created
