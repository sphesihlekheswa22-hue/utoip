"""Maintenance — preventive & corrective work-order management."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.models.assets import Asset
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.maintenance import (
    ASSET_LINK_TYPES,
    PLAN_FREQUENCIES,
    WO_PRIORITIES,
    WO_STATUSES,
    WO_TYPES,
)
from uitop.models.user import User
from uitop.services import maintenance as mt_svc

bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


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


@bp.get("/")
def index():
    view = request.args.get("view", "dashboard")
    allowed = {
        "dashboard",
        "scheduled",
        "work_orders",
        "completed",
        "recurring",
        "plans",
        "history",
        "reports",
    }
    if view not in allowed:
        view = "dashboard"

    list_view = view if view in ("scheduled", "work_orders", "completed", "history") else None
    if view == "history":
        rows = mt_svc.list_work_orders(view="completed")
    elif list_view:
        rows = mt_svc.list_work_orders(view=list_view)
    else:
        rows = mt_svc.list_work_orders()

    type_filter = request.args.get("type") or None
    if type_filter in WO_TYPES:
        rows = [r for r in rows if r["maintenance_type"] == type_filter]

    kpis = mt_svc.maintenance_kpis()
    plans = mt_svc.list_plans()

    # Lightweight report aggregates
    completed = [r for r in mt_svc.list_work_orders() if r["status"] == "completed"]
    cost_total = sum(float(r.get("total_cost") or 0) for r in completed)
    by_asset: dict[str, int] = {}
    for r in mt_svc.list_work_orders():
        label = r.get("asset_label") or "Unknown"
        by_asset[label] = by_asset.get(label, 0) + 1
    most_repaired = sorted(by_asset.items(), key=lambda x: -x[1])[:5]

    return render_template(
        "maintenance/index.html",
        active="maintenance",
        view=view,
        work_orders=rows,
        kpis=kpis,
        plans=plans,
        users=_form_users(),
        types=WO_TYPES,
        statuses=WO_STATUSES,
        priorities=WO_PRIORITIES,
        type_filter=type_filter or "",
        report={
            "cost_total": cost_total,
            "completed_count": len(completed),
            "most_repaired": most_repaired,
            "upcoming": mt_svc.list_work_orders(view="scheduled")[:8],
            "overdue": mt_svc.list_work_orders(view="overdue"),
        },
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    users = _form_users()
    inventory = _inventory_choices()
    plans = mt_svc.list_plans()
    if request.method == "POST":
        try:
            link_type = (request.form.get("linked_type") or "asset").strip()
            link_id = request.form.get("linked_id", type=int) or None
            checklist_raw = request.form.get("checklist") or ""
            checklist = [line.strip() for line in checklist_raw.splitlines() if line.strip()]
            wo = mt_svc.create_work_order(
                title=request.form.get("title"),
                description=request.form.get("description"),
                maintenance_type=request.form.get("maintenance_type") or "preventive",
                priority=request.form.get("priority") or "medium",
                linked_type=link_type,
                linked_id=link_id,
                technician_user_id=request.form.get("technician_user_id", type=int) or None,
                plan_id=request.form.get("plan_id", type=int) or None,
                location=request.form.get("location"),
                scheduled_at=request.form.get("scheduled_at"),
                due_at=request.form.get("due_at"),
                checklist=checklist or None,
                actor_id=session.get("user_id"),
            )
            flash(f"Work order {wo.work_order_number} created.", "success")
            return redirect(url_for("maintenance.details", item_id=wo.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "maintenance/create.html",
        active="maintenance",
        users=users,
        inventory=inventory,
        plans=plans,
        types=WO_TYPES,
        priorities=WO_PRIORITIES,
        link_types=ASSET_LINK_TYPES,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    try:
        detail = mt_svc.build_detail_payload(item_id)
    except APIError:
        abort(404)
    return render_template(
        "maintenance/details.html",
        active="maintenance",
        work_order=detail["work_order"],
        item_id=item_id,
        detail=detail,
        users=_form_users(),
        statuses=WO_STATUSES,
        priorities=WO_PRIORITIES,
        view=request.args.get("view", "overview"),
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    try:
        wo = mt_svc.get_wo_or_404(item_id)
    except APIError:
        abort(404)
    if request.method == "POST":
        try:
            mt_svc.update_work_order(
                item_id,
                {
                    "title": request.form.get("title"),
                    "description": request.form.get("description"),
                    "priority": request.form.get("priority"),
                    "maintenance_type": request.form.get("maintenance_type"),
                    "status": request.form.get("status"),
                    "location": request.form.get("location"),
                    "technician_user_id": request.form.get("technician_user_id", type=int) or None,
                    "labour_cost": request.form.get("labour_cost", type=float),
                    "travel_cost": request.form.get("travel_cost", type=float),
                    "other_cost": request.form.get("other_cost", type=float),
                },
                actor_id=session.get("user_id"),
            )
            flash("Work order updated.", "success")
            return redirect(url_for("maintenance.details", item_id=item_id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "maintenance/edit.html",
        active="maintenance",
        work_order=mt_svc.serialize_wo(wo),
        item_id=item_id,
        users=_form_users(),
        types=WO_TYPES,
        statuses=WO_STATUSES,
        priorities=WO_PRIORITIES,
    )


@bp.post("/<int:item_id>/status")
def set_status(item_id):
    try:
        mt_svc.update_work_order(
            item_id,
            {"status": request.form.get("status")},
            actor_id=session.get("user_id"),
        )
        flash("Status updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("maintenance.details", item_id=item_id, view=request.form.get("next_view") or "overview"))


@bp.post("/<int:item_id>/checklist/<int:check_id>")
def toggle_check(item_id, check_id):
    try:
        mt_svc.toggle_checklist(check_id, actor_id=session.get("user_id"))
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("maintenance.details", item_id=item_id, view="checklist"))


@bp.post("/<int:item_id>/parts")
def add_part(item_id):
    try:
        mt_svc.add_part(
            item_id,
            part_name=request.form.get("part_name"),
            quantity=request.form.get("quantity", type=int) or 1,
            unit_cost=request.form.get("unit_cost", type=float) or 0,
            notes=request.form.get("notes"),
            actor_id=session.get("user_id"),
        )
        flash("Part recorded.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("maintenance.details", item_id=item_id, view="parts"))


@bp.post("/<int:item_id>/costs")
def update_costs(item_id):
    try:
        mt_svc.update_work_order(
            item_id,
            {
                "labour_cost": request.form.get("labour_cost", type=float),
                "travel_cost": request.form.get("travel_cost", type=float),
                "other_cost": request.form.get("other_cost", type=float),
            },
            actor_id=session.get("user_id"),
        )
        flash("Costs updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("maintenance.details", item_id=item_id, view="costs"))


@bp.route("/plans/create", methods=["GET", "POST"])
def create_plan():
    if request.method == "POST":
        try:
            checklist_raw = request.form.get("checklist") or ""
            checklist = [line.strip() for line in checklist_raw.splitlines() if line.strip()]
            plan = mt_svc.create_plan(
                name=request.form.get("name"),
                description=request.form.get("description"),
                frequency=request.form.get("frequency") or "monthly",
                interval_days=request.form.get("interval_days", type=int),
                linked_type=request.form.get("linked_type") or None,
                checklist=checklist or None,
                actor_id=session.get("user_id"),
            )
            flash(f"Plan “{plan.name}” created.", "success")
            return redirect(url_for("maintenance.index", view="plans"))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "maintenance/plan_create.html",
        active="maintenance",
        frequencies=PLAN_FREQUENCIES,
        link_types=ASSET_LINK_TYPES,
    )


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("maintenance.details", item_id=item_id, view="timeline"))
