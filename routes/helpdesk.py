"""Helpdesk routes — live ticket queue."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.models.department import Department
from uitop.models.helpdesk import TICKET_CATEGORIES, TICKET_PRIORITIES, TICKET_STATUSES
from uitop.models.inventory import Computer
from uitop.models.user import User
from uitop.services import helpdesk as hd_svc

bp = Blueprint("helpdesk", __name__, url_prefix="/helpdesk")


def _form_users():
    return User.query.filter_by(is_active=True).order_by(User.full_name).all()


@bp.get("/")
def index():
    rows = hd_svc.list_tickets()
    return render_template(
        "helpdesk/index.html",
        active="helpdesk",
        tickets=rows,
        kpis=hd_svc.ticket_kpis(rows),
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    users = _form_users()
    departments = Department.query.order_by(Department.name).all()
    computers = Computer.query.order_by(Computer.hostname).all()
    if request.method == "POST":
        try:
            linked_id = request.form.get("linked_id", type=int) or None
            ticket = hd_svc.create_ticket(
                subject=request.form.get("subject"),
                description=request.form.get("description"),
                priority=request.form.get("priority") or "medium",
                category=request.form.get("category") or "other",
                requester_user_id=request.form.get("requester_user_id", type=int) or None,
                requester_name=request.form.get("requester_name"),
                assignee_user_id=request.form.get("assignee_user_id", type=int) or None,
                department_id=request.form.get("department_id", type=int) or None,
                location=request.form.get("location"),
                linked_type="computer" if linked_id else "none",
                linked_id=linked_id,
                actor_id=session.get("user_id"),
            )
            flash(f"Ticket {ticket.ticket_number} created.", "success")
            return redirect(url_for("helpdesk.details", item_id=ticket.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "helpdesk/create.html",
        active="helpdesk",
        users=users,
        departments=departments,
        computers=computers,
        priorities=TICKET_PRIORITIES,
        categories=TICKET_CATEGORIES,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    try:
        ticket = hd_svc.get_ticket_or_404(item_id)
    except APIError:
        abort(404)
    from uitop.models.helpdesk import TicketComment

    comments = [
        c.to_dict()
        for c in TicketComment.query.filter_by(ticket_id=ticket.id).order_by(TicketComment.created_at.asc()).all()
    ]
    return render_template(
        "helpdesk/details.html",
        active="helpdesk",
        ticket=hd_svc.serialize_ticket(ticket),
        item_id=item_id,
        comments=comments,
        users=_form_users(),
        statuses=TICKET_STATUSES,
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    try:
        ticket = hd_svc.get_ticket_or_404(item_id)
    except APIError:
        abort(404)
    users = _form_users()
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        try:
            hd_svc.update_ticket(
                item_id,
                {
                    "subject": request.form.get("subject"),
                    "description": request.form.get("description"),
                    "priority": request.form.get("priority"),
                    "category": request.form.get("category"),
                    "status": request.form.get("status"),
                    "location": request.form.get("location"),
                    "department_id": request.form.get("department_id", type=int) or None,
                    "requester_name": request.form.get("requester_name"),
                    "requester_user_id": request.form.get("requester_user_id", type=int) or None,
                    "assignee_user_id": request.form.get("assignee_user_id", type=int) or None,
                },
                actor_id=session.get("user_id"),
            )
            flash("Ticket updated.", "success")
            return redirect(url_for("helpdesk.details", item_id=item_id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "helpdesk/edit.html",
        active="helpdesk",
        ticket=hd_svc.serialize_ticket(ticket),
        item_id=item_id,
        users=users,
        departments=departments,
        priorities=TICKET_PRIORITIES,
        categories=TICKET_CATEGORIES,
        statuses=TICKET_STATUSES,
    )


@bp.post("/<int:item_id>/assign")
def assign(item_id):
    try:
        assignee = request.form.get("assignee_user_id", type=int) or None
        hd_svc.assign_ticket(item_id, assignee, actor_id=session.get("user_id"))
        flash("Assignee updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id))


@bp.post("/<int:item_id>/status")
def set_status(item_id):
    try:
        hd_svc.update_ticket(
            item_id,
            {"status": request.form.get("status")},
            actor_id=session.get("user_id"),
        )
        flash("Status updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id))


@bp.post("/<int:item_id>/comment")
def comment(item_id):
    try:
        hd_svc.add_comment(
            item_id,
            request.form.get("body"),
            actor_id=session.get("user_id"),
            is_internal=request.form.get("is_internal") == "1",
        )
        flash("Comment added.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id) + "#activity")


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("helpdesk.details", item_id=item_id) + "#activity")
