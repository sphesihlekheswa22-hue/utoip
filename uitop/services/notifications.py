"""In-app notification helpers."""
from __future__ import annotations

from uitop.extensions import db
from uitop.models.notifications import AppNotification


def notify_user(
    user_id: int | None,
    *,
    title: str,
    body: str | None = None,
    category: str = "general",
    link_url: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    actor_id: int | None = None,
    commit: bool = False,
) -> AppNotification | None:
    if not user_id:
        return None
    if actor_id and actor_id == user_id:
        return None  # don't notify yourself
    note = AppNotification(
        user_id=user_id,
        title=title[:255],
        body=(body or "")[:1024] or None,
        category=category or "general",
        link_url=link_url,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.session.add(note)
    if commit:
        db.session.commit()
    return note


def list_for_user(user_id: int, *, unread_only: bool = False, limit: int = 50) -> list[AppNotification]:
    q = AppNotification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)
    return q.order_by(AppNotification.created_at.desc()).limit(limit).all()


def unread_count(user_id: int) -> int:
    return AppNotification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_read(notification_id: int, user_id: int) -> AppNotification | None:
    note = AppNotification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not note:
        return None
    note.is_read = True
    db.session.commit()
    return note


def mark_all_read(user_id: int) -> int:
    rows = AppNotification.query.filter_by(user_id=user_id, is_read=False).all()
    for n in rows:
        n.is_read = True
    db.session.commit()
    return len(rows)


def notify_ticket_event(ticket, *, event: str, actor_id: int | None = None) -> None:
    """Create notifications for assignees / requesters on ticket events."""
    link = f"/helpdesk/{ticket.id}"
    number = ticket.ticket_number
    subject = ticket.subject

    if event == "created":
        if ticket.assignee_user_id:
            notify_user(
                ticket.assignee_user_id,
                title=f"Ticket assigned: {number}",
                body=subject,
                category="helpdesk",
                link_url=link,
                resource_type="ticket",
                resource_id=ticket.id,
                actor_id=actor_id,
            )
    elif event == "assigned":
        notify_user(
            ticket.assignee_user_id,
            title=f"You were assigned {number}",
            body=subject,
            category="helpdesk",
            link_url=link,
            resource_type="ticket",
            resource_id=ticket.id,
            actor_id=actor_id,
        )
    elif event == "commented":
        targets = {ticket.assignee_user_id, ticket.requester_user_id, ticket.created_by_id}
        for uid in targets:
            notify_user(
                uid,
                title=f"New comment on {number}",
                body=subject,
                category="helpdesk",
                link_url=f"{link}?view=comments",
                resource_type="ticket",
                resource_id=ticket.id,
                actor_id=actor_id,
            )
    elif event == "status":
        targets = {ticket.assignee_user_id, ticket.requester_user_id, ticket.created_by_id}
        for uid in targets:
            notify_user(
                uid,
                title=f"{number} is now {ticket.status.replace('_', ' ')}",
                body=subject,
                category="helpdesk",
                link_url=link,
                resource_type="ticket",
                resource_id=ticket.id,
                actor_id=actor_id,
            )
