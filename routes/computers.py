"""Computers module — live DB + agent telemetry UI."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.models.auth import AgentEnrollmentToken
from uitop.services import agents as agents_service
from uitop.services import computers_view as computers_svc

bp = Blueprint("computers", __name__, url_prefix="/computers")


@bp.get("/")
def index():
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else computers_svc.list_computers_for_ui()
    departments = computers_svc.department_names()
    return render_template(
        "computers/index.html",
        active="computers",
        computers=rows,
        kpis=computers_svc.computer_kpis(rows),
        empty=empty_flag or not rows,
        departments=departments,
    )


@bp.get("/install-agent")
def install_agent():
    tokens = (
        AgentEnrollmentToken.query.order_by(AgentEnrollmentToken.created_at.desc()).limit(10).all()
    )
    return render_template(
        "computers/install-agent.html",
        active="computers",
        enrollment_tokens=[t.to_dict() for t in tokens],
        raw_token=session.pop("enrollment_token_raw", None),
        server_url=request.url_root.rstrip("/"),
    )


@bp.post("/install-agent/token")
def create_enrollment_token():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))

    label = (request.form.get("label") or "Computers enroll").strip()
    token, raw = agents_service.create_enrollment_token(
        label=label,
        created_by_id=user_id,
        expires_hours=int(request.form.get("expires_hours") or 168),
        max_uses=int(request.form.get("max_uses") or 50),
    )
    session["enrollment_token_raw"] = raw
    flash(f"Enrollment token created ({token.token_prefix}…). Copy it now — it won't be shown again.", "success")
    return redirect(url_for("computers.install_agent"))


@bp.get("/scan-network")
def scan_network():
    return render_template("computers/scan-network.html", active="computers")


@bp.get("/create")
def create():
    """Legacy URL — redirect to Install Agent."""
    return redirect(url_for("computers.install_agent"))


@bp.get("/<int:item_id>")
def details(item_id):
    computer = computers_svc.get_computer_or_none(item_id)
    if computer is None:
        abort(404)
    device = computers_svc.serialize_computer(computer)
    tab = request.args.get("tab", "overview")
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("computer", item_id)
    return render_template(
        "computers/details.html",
        active="computers",
        device=device,
        item_id=item_id,
        initial_tab=tab,
        perf_series=computers_svc.performance_series(item_id),
        agent_events=computers_svc.recent_events(item_id),
        agent_alerts=computers_svc.recent_alerts(item_id),
        linked_files=linked_files,
    )


@bp.get("/<int:item_id>/edit")
def edit(item_id):
    return redirect(url_for("computers.details", item_id=item_id, tab="overview"))


@bp.get("/<int:item_id>/<page>")
def device_page(item_id, page):
    """Map old sub-routes into details tabs."""
    mapping = {
        "performance": "performance",
        "software": "software",
        "services": "services",
        "event-logs": "events",
        "network": "network",
        "processes": "processes",
        "remote-access": "remote",
        "history": "timeline",
        "delete": "overview",
    }
    tab = mapping.get(page, "overview")
    return redirect(url_for("computers.details", item_id=item_id, tab=tab))
