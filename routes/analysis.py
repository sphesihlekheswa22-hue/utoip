"""Analysis — executive decision-making insights hub."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from uitop.services import analysis_view as av

bp = Blueprint("analysis", __name__, url_prefix="/analysis")


@bp.get("/")
def index():
    view = request.args.get("view", "executive")
    allowed = {
        "executive",
        "infrastructure",
        "assets",
        "helpdesk",
        "performance",
        "security",
        "maintenance",
        "financial",
        "forecasts",
        "reports",
    }
    if view not in allowed:
        view = "executive"
    payload = av.build_module_payload()
    return render_template(
        "analysis/index.html",
        active="analysis",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
    )


@bp.get("/details")
def details():
    return redirect(url_for("analysis.index", view="executive"))
