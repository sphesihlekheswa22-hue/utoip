"""Audit Logs — read-only compliance console."""
from __future__ import annotations

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for

from uitop.services import audit_view as av
from uitop.utils.pagination import paginate

bp = Blueprint("audit", __name__, url_prefix="/audit")

ALLOWED = {"dashboard", "events", "failed", "config", "critical", "legend"}


@bp.get("/")
def index():
    view = request.args.get("view", "dashboard")
    if view not in ALLOWED:
        view = "dashboard"
    # Seed illustrative rows once if empty
    if session.get("user_id"):
        av.ensure_sample_events(actor_id=session.get("user_id"))
    payload = av.build_module_payload(
        category=request.args.get("category", ""),
        severity=request.args.get("severity", ""),
        result=request.args.get("result", ""),
        actor_id=request.args.get("actor_id", type=int),
        q=request.args.get("q", ""),
        days=request.args.get("days", 30, type=int) or 30,
    )
    if view == "failed":
        events_list = payload["failed"]
    elif view == "config":
        events_list = payload["config"]
    elif view == "critical":
        events_list = payload["critical"]
    else:
        events_list = payload["events"]
    pager = paginate(events_list, request.args.get("page", type=int))
    return render_template(
        "audit/index.html",
        active="audit",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
        pager=pager,
        events=pager["items"],
    )


@bp.get("/<int:item_id>")
def details(item_id: int):
    event = av.get_event(item_id)
    if event is None:
        flash("Audit event not found.", "error")
        return redirect(url_for("audit.index", view="events"))
    return render_template("audit/details.html", active="audit", event=event, item_id=item_id)


@bp.get("/export")
def export_csv():
    payload = av.build_module_payload(
        category=request.args.get("category", ""),
        severity=request.args.get("severity", ""),
        result=request.args.get("result", ""),
        actor_id=request.args.get("actor_id", type=int),
        q=request.args.get("q", ""),
        days=request.args.get("days", 90, type=int) or 90,
    )
    body = av.to_csv(payload["events"])
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="UITOP_Audit_Logs.csv"'},
    )
