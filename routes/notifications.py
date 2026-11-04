"""In-app notifications routes."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, session, url_for

from uitop.services import notifications as notif_svc

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.get("/")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    notes = notif_svc.list_for_user(user_id, limit=80)
    unread = notif_svc.unread_count(user_id)
    return render_template(
        "notifications/index.html",
        active="notifications",
        notifications=[n.to_dict() for n in notes],
        unread_count=unread,
    )


@bp.post("/<int:note_id>/read")
def mark_read(note_id: int):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    note = notif_svc.mark_read(note_id, user_id)
    if note and note.link_url:
        return redirect(note.link_url)
    return redirect(url_for("notifications.index"))


@bp.post("/read-all")
def read_all():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    n = notif_svc.mark_all_read(user_id)
    flash(f"Marked {n} notification(s) as read.", "success")
    return redirect(url_for("notifications.index"))
