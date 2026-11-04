"""Workflows & Tasks — restore requests and cross-module work items."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.core.ui_rbac import has_perm, is_employee_session, is_super_admin_session
from uitop.models.inventory import Computer
from uitop.models.user import User
from uitop.services import employee_view as emp
from uitop.services import workflow as wf

bp = Blueprint("workflows", __name__, url_prefix="/workflows")
tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def _uid():
    return session.get("user_id")


def _can_staff_queue() -> bool:
    return is_super_admin_session() or has_perm("helpdesk:assign", "backup:manage", "backup:read") and not is_employee_session()


@bp.get("/")
def index():
    wf.ensure_workflow_definitions()
    uid = _uid()
    view = request.args.get("view", "mine" if is_employee_session() else "queue")
    if is_employee_session() or view == "mine":
        rows = wf.list_instances(requester_user_id=uid)
        view = "mine"
    else:
        status = request.args.get("status") or None
        rows = wf.list_instances(status=status, definition_key=request.args.get("type") or None)
    return render_template(
        "workflows/index.html",
        active="workflows",
        view=view,
        instances=[r.to_dict() for r in rows],
        is_employee=is_employee_session(),
    )


@bp.route("/restore/request", methods=["GET", "POST"])
def restore_request():
    uid = _uid()
    if not uid:
        return redirect(url_for("auth.login"))
    devices = emp.list_my_devices(uid)
    computers = devices.get("computers") or []
    # Staff can pick any live computer label
    if not is_employee_session() and has_perm("computers:read"):
        computers = [
            c.to_dict()
            for c in Computer.query.filter(Computer.agent_id.isnot(None))
            .order_by(Computer.hostname)
            .limit(50)
            .all()
        ]

    if request.method == "POST":
        label = (request.form.get("resource_label") or "").strip()
        resource_id = request.form.get("resource_id", type=int)
        try:
            inst = wf.start_restore_request(
                requester_id=uid,
                title=request.form.get("title") or f"Restore — {label or 'files'}",
                reason=request.form.get("reason"),
                resource_label=label,
                resource_type="computer",
                resource_id=resource_id,
                priority=request.form.get("priority") or "medium",
                backup_point=request.form.get("backup_point"),
            )
            flash(f"Restore request {inst.number} submitted.", "success")
            return redirect(url_for("workflows.details", item_id=inst.id))
        except APIError as err:
            flash(err.message, "error")

    return render_template(
        "workflows/restore_request.html",
        active="workflows",
        computers=computers,
        is_employee=is_employee_session(),
    )


@bp.get("/<int:item_id>")
def details(item_id):
    from uitop.extensions import db
    from uitop.models.workflow import WorkflowInstance

    inst = db.session.get(WorkflowInstance, item_id)
    if not inst:
        abort(404)
    uid = _uid()
    # Employees only see own requests
    if is_employee_session() and inst.requester_user_id != uid and not is_super_admin_session():
        flash("You can only view your own requests.", "error")
        return redirect(url_for("workflows.index"))

    detail = wf.serialize_instance_detail(inst)
    step = detail.get("current_step")
    can_act = wf.can_act_on_step(step, user_id=uid) and inst.status not in (
        "completed",
        "rejected",
        "cancelled",
    )
    users = []
    if can_act and not is_employee_session():
        users = User.query.filter_by(is_active=True).order_by(User.full_name).limit(80).all()

    return render_template(
        "workflows/details.html",
        active="workflows",
        item_id=item_id,
        detail=detail,
        instance=detail,
        can_act=can_act,
        users=users,
        is_employee=is_employee_session(),
    )


@bp.post("/<int:item_id>/action")
def action(item_id):
    try:
        wf.advance_instance(
            item_id,
            action=request.form.get("action"),
            actor_id=_uid(),
            note=request.form.get("note"),
            assignee_user_id=request.form.get("assignee_user_id", type=int),
        )
        flash("Workflow updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("workflows.details", item_id=item_id))


@tasks_bp.get("/")
def index():
    uid = _uid()
    view = request.args.get("view", "mine")
    if view == "all" and not is_employee_session():
        rows = wf.list_tasks(open_only=request.args.get("open") == "1")
    elif view == "queue" and not is_employee_session():
        rows = wf.list_tasks(open_only=True)
    else:
        rows = wf.list_tasks(assignee_user_id=uid, open_only=False)
        # Also show unassigned queue items for staff on "mine" if empty? Keep mine = assigned to me
        view = "mine"
    return render_template(
        "tasks/index.html",
        active="tasks",
        view=view,
        tasks=[t.to_dict() for t in rows],
        is_employee=is_employee_session(),
    )


@tasks_bp.post("/<int:item_id>/update")
def update(item_id):
    try:
        wf.update_task(
            item_id,
            actor_id=_uid(),
            status=request.form.get("status"),
            assignee_user_id=request.form.get("assignee_user_id", type=int),
            priority=request.form.get("priority"),
        )
        flash("Task updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(request.referrer or url_for("tasks.index"))
