"""Printers module — live DB inventory + SNMP actions."""
from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.services import inventory_view as inv
from uitop.services import printer_snmp as prn_svc

bp = Blueprint("printers", __name__, url_prefix="/printers")


@bp.get("/")
def index():
    from uitop.core.ui_rbac import is_employee_session

    if is_employee_session():
        return redirect(url_for("employee.devices"))
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else inv.list_printers_for_ui()
    return render_template(
        "printers/index.html",
        active="printers",
        printers=rows,
        kpis=inv.printer_kpis(rows),
        empty=empty_flag or not rows,
    )


@bp.get("/discover")
def discover():
    return render_template("printers/discover.html", active="printers")


@bp.get("/create")
def create():
    return redirect(url_for("printers.discover"))


@bp.get("/<int:item_id>")
def details(item_id):
    from uitop.models.inventory import Printer

    row = Printer.query.get(item_id)
    if row is None:
        abort(404)
    printer = inv.serialize_printer(row)
    tab = request.args.get("tab", "overview")
    profiles = [p.to_dict(include_secret=False) for p in prn_svc.list_profiles()]
    return render_template(
        "printers/details.html",
        active="printers",
        printer=printer,
        item_id=item_id,
        initial_tab=tab,
        snmp_profiles=profiles,
    )


@bp.post("/<int:item_id>/remote/<action>")
def remote_action(item_id, action):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Sign in required"}), 401
    try:
        result = prn_svc.run_action(item_id, action, actor_user_id=user_id)
    except APIError as exc:
        return jsonify({"error": exc.message}), getattr(exc, "status_code", 400)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.post("/<int:item_id>/snmp-profile")
def assign_snmp_profile(item_id):
    from uitop.extensions import db
    from uitop.models.inventory import Printer

    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))
    row = Printer.query.get(item_id)
    if row is None:
        abort(404)
    profile_id = request.form.get("snmp_profile_id") or ""
    row.snmp_profile_id = int(profile_id) if profile_id.isdigit() else None
    db.session.commit()
    flash("SNMP profile updated.", "success")
    return redirect(url_for("printers.details", item_id=item_id, tab="snmp"))


@bp.get("/<int:item_id>/<page>")
def printer_page(item_id, page):
    return redirect(url_for("printers.details", item_id=item_id, tab="overview"))
