"""Helpdesk / ITSM routes — service management workflow."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.core.ui_rbac import has_perm, is_employee_session
from uitop.models.assets import Asset
from uitop.models.department import Department
from uitop.models.helpdesk import (
    OBJECT_LINK_TYPES,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    TICKET_TYPES,
)
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User
from uitop.services import employee_view as emp_svc
from uitop.services import helpdesk as hd_svc
from uitop.services import knowledge as kb_svc

bp = Blueprint("helpdesk", __name__, url_prefix="/helpdesk")


def _employee_ticket_guard(item_id: int):
    """Employees may only access their own tickets."""
    if not is_employee_session():
        return None
    if emp_svc.user_owns_ticket(item_id):
        return None
    flash("You can only view tickets you created.", "error")
    return redirect(url_for("employee.tickets"))


def _form_users():
    return User.query.filter_by(is_active=True).order_by(User.full_name).all()


def _inventory_choices():
    return {
        "computers": Computer.query.order_by(Computer.hostname).all(),
        "servers": Server.query.order_by(Server.hostname).all(),
        "printers": Printer.query.order_by(Printer.name).all(),
        "network": NetworkDevice.query.order_by(NetworkDevice.hostname).all(),
        "assets": Asset.query.order_by(Asset.asset_tag).all(),
    }


def _sla_board(tickets: list[dict]) -> dict:
    """Live SLA board from ticket rows."""
    open_rows = [t for t in tickets if t.get("status") not in ("resolved", "closed")]
    overdue = [t for t in open_rows if t.get("overdue") or t.get("sla_breached")]
    by_priority = {p: 0 for p in TICKET_PRIORITIES}
    for t in open_rows:
        p = t.get("priority") or "medium"
        if p in by_priority:
            by_priority[p] += 1
    return {
        "targets": [
            {"priority": "critical", "respond": "15 minutes", "resolve": "2 hours"},
            {"priority": "high", "respond": "1 hour", "resolve": "8 hours"},
            {"priority": "medium", "respond": "4 hours", "resolve": "24 hours"},
            {"priority": "low", "respond": "8 hours", "resolve": "72 hours"},
        ],
        "open": len(open_rows),
        "overdue": overdue[:25],
        "overdue_count": len(overdue),
        "open_by_priority": by_priority,
    }


@bp.get("/")
def index():
    view = request.args.get("view", "dashboard")
    if is_employee_session() and view != "knowledge":
        return redirect(url_for("employee.tickets"))

    allowed = {
        "dashboard",
        "tickets",
        "incidents",
        "service_requests",
        "problems",
        "knowledge",
        "remote",
        "sla",
        "reports",
    }
    if view not in allowed:
        view = "dashboard"

    type_filter = None
    if view == "incidents":
        type_filter = "incident"
    elif view == "service_requests":
        type_filter = "service_request"
    elif view == "problems":
        type_filter = "problem"

    mine = request.args.get("mine") == "1"
    actor_id = session.get("user_id")
    rows = hd_svc.list_tickets(
        ticket_type=type_filter,
        assignee_user_id=actor_id if mine else None,
        priority=request.args.get("priority") or None,
        status=request.args.get("status") or None,
        department_id=request.args.get("department_id", type=int),
    )
    if view in ("dashboard", "tickets", "sla", "reports", "knowledge", "remote") and not type_filter:
        if not (mine or request.args.get("priority") or request.args.get("status") or request.args.get("department_id")):
            rows = hd_svc.list_tickets()

    kpis = hd_svc.ticket_kpis(rows if view != "dashboard" else None, assignee_user_id=actor_id)
    if view == "dashboard":
        rows = hd_svc.list_tickets()
        kpis = hd_svc.ticket_kpis(rows, assignee_user_id=actor_id)

    kb_articles = []
    kb_q = (request.args.get("q") or "").strip()
    kb_category = (request.args.get("category") or "").strip() or None
    if view == "knowledge":
        kb_svc.ensure_starter_articles(author_user_id=actor_id)
        kb_articles = [
            a.to_dict()
            for a in kb_svc.list_articles(
                q=kb_q or None,
                category=kb_category,
                published_only=is_employee_session(),
            )
        ]

    all_for_sla = hd_svc.list_tickets() if view in ("sla", "reports") else rows
    sla = _sla_board(all_for_sla) if view in ("sla", "reports", "dashboard") else None

    return render_template(
        "helpdesk/index.html",
        active="knowledge" if view == "knowledge" and is_employee_session() else "helpdesk",
        view=view,
        tickets=rows,
        kpis=kpis,
        sla=sla,
        kb_articles=kb_articles,
        kb_q=kb_q,
        kb_category=kb_category or "",
        departments=Department.query.order_by(Department.name).all(),
        users=_form_users(),
        priorities=TICKET_PRIORITIES,
        statuses=TICKET_STATUSES,
        ticket_types=TICKET_TYPES,
        mine=mine,
        filters={
            "priority": request.args.get("priority") or "",
            "status": request.args.get("status") or "",
            "department_id": request.args.get("department_id") or "",
        },
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    users = _form_users()
    departments = Department.query.order_by(Department.name).all()
    inventory = _inventory_choices()
    from uitop.models.helpdesk import Ticket

    problems = Ticket.query.filter_by(ticket_type="problem").order_by(Ticket.id.desc()).all()
    employee_mode = is_employee_session()
    actor_id = session.get("user_id")
    actor = User.query.get(actor_id) if actor_id else None

    if request.method == "POST":
        try:
            link_type = (request.form.get("link_type") or "none").strip()
            link_id = request.form.get("link_id", type=int) or None
            if link_type == "none":
                link_type, link_id = "none", None
            # Prefill from query (employee report-device shortcut)
            if request.args.get("link_type") and not request.form.get("link_type"):
                link_type = request.args.get("link_type") or link_type
                link_id = request.args.get("link_id", type=int) or link_id

            requester_user_id = request.form.get("requester_user_id", type=int) or None
            requester_name = request.form.get("requester_name")
            assignee_user_id = request.form.get("assignee_user_id", type=int) or None
            department_id = request.form.get("department_id", type=int) or None
            if employee_mode and actor:
                requester_user_id = actor.id
                requester_name = actor.full_name
                assignee_user_id = None
                department_id = department_id or actor.department_id

            ticket = hd_svc.create_ticket(
                subject=request.form.get("subject") or request.args.get("subject"),
                description=request.form.get("description"),
                priority=request.form.get("priority") or "medium",
                category=request.form.get("category") or "other",
                ticket_type=request.form.get("ticket_type") or "incident",
                requester_user_id=requester_user_id,
                requester_name=requester_name,
                assignee_user_id=assignee_user_id,
                department_id=department_id,
                location=request.form.get("location"),
                linked_type=link_type,
                linked_id=link_id,
                problem_id=None if employee_mode else request.form.get("problem_id", type=int) or None,
                actor_id=actor_id,
            )
            extra_type = (request.form.get("extra_link_type") or "").strip()
            extra_id = request.form.get("extra_link_id", type=int)
            if extra_type in OBJECT_LINK_TYPES and extra_id:
                hd_svc.add_object_link(ticket, extra_type, extra_id, actor_id=actor_id, commit=True)
            flash(f"Ticket {ticket.ticket_number} created.", "success")
            return redirect(url_for("helpdesk.details", item_id=ticket.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "helpdesk/create.html",
        active="helpdesk",
        users=[] if employee_mode else users,
        departments=departments,
        computers=inventory["computers"],
        inventory=inventory,
        problems=[] if employee_mode else problems,
        priorities=TICKET_PRIORITIES,
        categories=TICKET_CATEGORIES,
        ticket_types=TICKET_TYPES,
        link_types=OBJECT_LINK_TYPES,
        employee_mode=employee_mode,
        actor=actor,
        prefill_subject=request.args.get("subject") or "",
    )


@bp.get("/<int:item_id>")
def details(item_id):
    denied = _employee_ticket_guard(item_id)
    if denied:
        return denied
    try:
        detail = hd_svc.build_detail_payload(item_id)
    except APIError:
        abort(404)
    inventory = _inventory_choices()
    return render_template(
        "helpdesk/details.html",
        active="helpdesk",
        ticket=detail["ticket"],
        item_id=item_id,
        detail=detail,
        comments=detail["comments"],
        users=[] if is_employee_session() else _form_users(),
        statuses=TICKET_STATUSES,
        inventory=inventory,
        link_types=OBJECT_LINK_TYPES,
        view=request.args.get("view", "overview"),
        employee_mode=is_employee_session(),
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    denied = _employee_ticket_guard(item_id)
    if denied:
        return denied
    if is_employee_session() and not has_perm("helpdesk:assign"):
        flash("Ask Help Desk to update ticket fields. You can add comments or close resolved tickets.", "error")
        return redirect(url_for("helpdesk.details", item_id=item_id))
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
                    "ticket_type": request.form.get("ticket_type"),
                    "status": request.form.get("status"),
                    "location": request.form.get("location"),
                    "department_id": request.form.get("department_id", type=int) or None,
                    "requester_name": request.form.get("requester_name"),
                    "requester_user_id": request.form.get("requester_user_id", type=int) or None,
                    "assignee_user_id": request.form.get("assignee_user_id", type=int) or None,
                    "problem_id": request.form.get("problem_id", type=int) or None,
                },
                actor_id=session.get("user_id"),
            )
            flash("Ticket updated.", "success")
            return redirect(url_for("helpdesk.details", item_id=item_id))
        except APIError as err:
            flash(err.message, "error")
    from uitop.models.helpdesk import Ticket

    problems = Ticket.query.filter_by(ticket_type="problem").order_by(Ticket.id.desc()).all()
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
        ticket_types=TICKET_TYPES,
        problems=problems,
    )


@bp.post("/<int:item_id>/assign")
def assign(item_id):
    try:
        assignee = request.form.get("assignee_user_id", type=int) or None
        hd_svc.assign_ticket(item_id, assignee, actor_id=session.get("user_id"))
        flash("Assignee updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id, view="overview"))


@bp.post("/<int:item_id>/status")
def set_status(item_id):
    denied = _employee_ticket_guard(item_id)
    if denied:
        return denied
    status = request.form.get("status")
    if is_employee_session() and status not in ("resolved", "closed"):
        flash("Employees can only close or mark resolved on their own tickets.", "error")
        return redirect(url_for("helpdesk.details", item_id=item_id, view="overview"))
    try:
        hd_svc.update_ticket(
            item_id,
            {"status": status},
            actor_id=session.get("user_id"),
        )
        flash("Status updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    view = request.form.get("next_view") or "overview"
    return redirect(url_for("helpdesk.details", item_id=item_id, view=view))


@bp.post("/<int:item_id>/comment")
def comment(item_id):
    denied = _employee_ticket_guard(item_id)
    if denied:
        return denied
    try:
        hd_svc.add_comment(
            item_id,
            request.form.get("body"),
            actor_id=session.get("user_id"),
            is_internal=False if is_employee_session() else request.form.get("is_internal") == "1",
        )
        flash("Comment added.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id, view="comments"))


@bp.post("/<int:item_id>/link")
def add_link(item_id):
    try:
        ticket = hd_svc.get_ticket_or_404(item_id)
        link_type = (request.form.get("link_type") or "").strip()
        link_id = request.form.get("link_id", type=int)
        if not link_type or not link_id:
            flash("Select an object to link.", "error")
        else:
            hd_svc.add_object_link(
                ticket,
                link_type,
                link_id,
                actor_id=session.get("user_id"),
                commit=True,
            )
            flash("Object linked to ticket.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id, view="assets"))


@bp.post("/<int:item_id>/time")
def add_time(item_id):
    try:
        hd_svc.add_time_log(
            item_id,
            started_at=request.form.get("started_at"),
            finished_at=request.form.get("finished_at"),
            minutes=request.form.get("minutes", type=int),
            note=request.form.get("note"),
            actor_id=session.get("user_id"),
        )
        flash("Time logged.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.details", item_id=item_id, view="timelog"))


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("helpdesk.details", item_id=item_id, view="activity"))


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

@bp.route("/knowledge/new", methods=["GET", "POST"])
def knowledge_create():
    from uitop.models.helpdesk import KB_CATEGORIES

    if request.method == "POST":
        try:
            article = kb_svc.create_article(
                title=request.form.get("title"),
                body=request.form.get("body"),
                summary=request.form.get("summary"),
                category=request.form.get("category") or "general",
                tags=request.form.get("tags"),
                is_published=request.form.get("is_published") == "1",
                author_user_id=session.get("user_id"),
            )
            flash("Knowledge article published.", "success")
            return redirect(url_for("helpdesk.knowledge_detail", article_id=article.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "helpdesk/knowledge_form.html",
        active="helpdesk",
        article=None,
        categories=KB_CATEGORIES,
    )


@bp.get("/knowledge/<int:article_id>")
def knowledge_detail(article_id):
    try:
        article = kb_svc.record_view(article_id)
    except APIError:
        abort(404)
    return render_template(
        "helpdesk/knowledge_detail.html",
        active="helpdesk",
        article=article.to_dict(),
        article_id=article_id,
    )


@bp.route("/knowledge/<int:article_id>/edit", methods=["GET", "POST"])
def knowledge_edit(article_id):
    from uitop.models.helpdesk import KB_CATEGORIES

    try:
        article = kb_svc.get_article(article_id)
    except APIError:
        abort(404)
    if request.method == "POST":
        try:
            kb_svc.update_article(
                article_id,
                {
                    "title": request.form.get("title"),
                    "body": request.form.get("body"),
                    "summary": request.form.get("summary"),
                    "category": request.form.get("category"),
                    "tags": request.form.get("tags"),
                    "is_published": request.form.get("is_published") == "1",
                },
            )
            flash("Article updated.", "success")
            return redirect(url_for("helpdesk.knowledge_detail", article_id=article_id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "helpdesk/knowledge_form.html",
        active="helpdesk",
        article=article.to_dict(),
        categories=KB_CATEGORIES,
    )


@bp.post("/knowledge/<int:article_id>/helpful")
def knowledge_helpful(article_id):
    try:
        kb_svc.mark_helpful(article_id)
        flash("Thanks — marked as helpful.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.knowledge_detail", article_id=article_id))


@bp.post("/knowledge/<int:article_id>/delete")
def knowledge_delete(article_id):
    try:
        kb_svc.delete_article(article_id)
        flash("Article deleted.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("helpdesk.index", view="knowledge"))


# ---------------------------------------------------------------------------
# Reports export
# ---------------------------------------------------------------------------

@bp.get("/export.csv")
def export_csv():
    import csv
    from io import StringIO

    from flask import Response

    rows = hd_svc.list_tickets(
        ticket_type=request.args.get("ticket_type") or None,
        priority=request.args.get("priority") or None,
        status=request.args.get("status") or None,
        department_id=request.args.get("department_id", type=int),
    )
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Ticket",
            "Subject",
            "Type",
            "Status",
            "Priority",
            "Category",
            "Requester",
            "Assignee",
            "Department",
            "Created",
            "SLA due",
            "Overdue",
        ]
    )
    for t in rows:
        writer.writerow(
            [
                t.get("ticket_number"),
                t.get("subject"),
                t.get("ticket_type"),
                t.get("status"),
                t.get("priority"),
                t.get("category"),
                t.get("requester"),
                t.get("assignee"),
                t.get("department"),
                t.get("created_at") or t.get("created"),
                t.get("sla_due_at"),
                "yes" if t.get("overdue") or t.get("sla_breached") else "no",
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=helpdesk-tickets.csv"},
    )
