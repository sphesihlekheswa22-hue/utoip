"""IT Operations Calendar — aggregated timeline across UITOP."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from uitop.services import calendar_view as cal

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@bp.get("/")
def index():
    view = request.args.get("view", "month")
    allowed = {"month", "week", "day", "agenda", "timeline"}
    if view not in allowed:
        view = "month"
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    day = request.args.get("day")
    payload = cal.build_module_payload(view=view, year=year, month=month, day=day)
    return render_template(
        "calendar/index.html",
        active="calendar",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
    )


@bp.get("/event/<path:event_id>")
def event_detail(event_id):
    detail = cal.get_event_detail(event_id)
    if not detail:
        abort(404)
    # Prefer deep-link into source module when available
    if detail.get("url"):
        return redirect(detail["url"])
    return render_template(
        "calendar/details.html",
        active="calendar",
        event=detail,
    )


@bp.get("/create")
def create():
    # Ops calendar does not create arbitrary appointments
    return redirect(url_for("calendar.index", view="agenda"))


@bp.get("/<path:page_name>")
def legacy(page_name):
    if page_name in ("details", "create"):
        return redirect(url_for("calendar.index"))
    abort(404)
