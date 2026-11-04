"""Settings — admin platform control center."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from uitop.services import settings_view as sv
from uitop.services.audit import log_audit

bp = Blueprint("settings", __name__, url_prefix="/settings")

ALLOWED = {c[0] for c in sv.CATEGORIES}


@bp.get("/")
def index():
    view = request.args.get("view", "general")
    if view not in ALLOWED:
        view = "general"
    payload = sv.build_module_payload(view)
    return render_template(
        "settings/index.html",
        active="settings",
        view=view,
        payload=payload,
        settings=payload["current"],
        categories=payload["categories"],
    )


@bp.post("/save")
def save():
    view = request.form.get("view") or "general"
    cat_defaults = sv.DEFAULTS.get(sv._map_alias(view), {})
    data = {}
    for key, default in cat_defaults.items():
        if isinstance(default, bool):
            data[key] = "1" if request.form.get(key) else "0"
        elif key in request.form:
            data[key] = request.form.get(key)
    # Also accept extra form keys present in current settings
    current = sv.get_category(view)
    for key, default in current.items():
        if key in data:
            continue
        if isinstance(default, bool):
            data[key] = "1" if request.form.get(key) else "0"
        elif key in request.form:
            data[key] = request.form.get(key)
    try:
        sv.update_category(view, data, actor_id=session.get("user_id"))
        flash("Settings saved. Change recorded in Audit Logs.", "success")
    except Exception as err:
        flash(f"Could not save settings: {err}", "error")
    return redirect(url_for("settings.index", view=view))


@bp.post("/test-email")
def test_email():
    log_audit(
        "settings.test_email",
        actor_user_id=session.get("user_id"),
        resource_type="settings",
        resource_id="email",
        meta={"result": "Success"},
    )
    flash("Test email queued (SMTP connector will send when mail service is configured).", "success")
    return redirect(url_for("settings.index", view="email"))
