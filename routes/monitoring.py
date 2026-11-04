"""Infrastructure Monitoring — operational center of UITOP."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from uitop.services import monitoring_view as mon

bp = Blueprint("monitoring", __name__, url_prefix="/monitoring")


@bp.get("/")
def index():
    view = request.args.get("view", "overview")
    allowed = {
        "overview",
        "health",
        "live",
        "performance",
        "network",
        "servers",
        "computers",
        "services",
        "processes",
        "alerts",
        "events",
        "reports",
    }
    if view not in allowed:
        view = "overview"
    payload = mon.build_module_payload()
    return render_template(
        "monitoring/index.html",
        active="monitoring",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    kind = (request.args.get("kind") or "computer").lower()
    detail = mon.build_device_payload(item_id, kind=kind)
    if not detail:
        # Fall back to computer redirect attempt
        if kind == "computer":
            return redirect(url_for("computers.details", item_id=item_id, tab="performance"))
        abort(404)
    return render_template(
        "monitoring/details.html",
        active="monitoring",
        item_id=item_id,
        kind=kind,
        detail=detail,
        device=detail["device"],
        view=request.args.get("view", "overview"),
    )


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("monitoring.details", item_id=item_id, view="history", kind=request.args.get("kind", "computer")))
