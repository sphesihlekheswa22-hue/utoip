"""Security posture & compliance center."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.services import security_view as sec

bp = Blueprint("security", __name__, url_prefix="/security")


@bp.get("/")
def index():
    view = request.args.get("view", "overview")
    allowed = {
        "overview",
        "threats",
        "vulnerabilities",
        "compliance",
        "antivirus",
        "firewall",
        "users",
        "devices",
        "incidents",
        "policies",
        "audit",
        "reports",
    }
    if view not in allowed:
        view = "overview"
    payload = sec.build_module_payload()
    return render_template(
        "security/index.html",
        active="security",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
    )


@bp.get("/device/<int:item_id>")
def device(item_id):
    detail = sec.build_device_payload(item_id)
    if not detail:
        abort(404)
    return render_template(
        "security/device.html",
        active="security",
        item_id=item_id,
        detail=detail,
        device=detail["device"],
        posture=detail["posture"],
        view=request.args.get("view", "overview"),
    )


@bp.post("/incidents/<int:item_id>/status")
def incident_status(item_id):
    row = sec.update_incident_status(item_id, (request.form.get("status") or "").strip())
    if not row:
        abort(404)
    flash(f"Incident {row.incident_number} updated.", "success")
    return redirect(url_for("security.index", view="incidents"))


@bp.post("/threats/<int:item_id>/status")
def threat_status(item_id):
    row = sec.update_threat_status(item_id, (request.form.get("status") or "").strip())
    if not row:
        abort(404)
    flash("Threat status updated.", "success")
    return redirect(url_for("security.index", view="threats"))


@bp.get("/create")
def create():
    return redirect(url_for("security.index", view="incidents"))


@bp.get("/<int:item_id>")
def details(item_id):
    # Legacy scaffold path → device security
    return redirect(url_for("security.device", item_id=item_id))
