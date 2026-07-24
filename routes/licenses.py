"""Licenses module — seat tracking & compliance UI (mock data)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from uitop.services import licenses_view as lic

bp = Blueprint("licenses", __name__, url_prefix="/licenses")


@bp.get("/")
def index():
    data = lic.build_module_payload()
    return render_template(
        "licenses/index.html",
        active="licenses",
        kpis=data["kpis"],
        payload=data,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = lic.build_detail_payload(item_id)
    if not detail:
        abort(404)
    return render_template(
        "licenses/details.html",
        active="licenses",
        item_id=item_id,
        detail=detail,
        license=detail["license"],
        view=request.args.get("view", "overview"),
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        flash("License recorded (demo — backend wiring next).", "success")
        return redirect(url_for("licenses.index"))
    return render_template("licenses/create.html", active="licenses")


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    license_row = lic.get_license(item_id)
    if not license_row:
        abort(404)
    if request.method == "POST":
        flash(f"{license_row['product']} updated (demo).", "success")
        return redirect(url_for("licenses.details", item_id=item_id))
    return render_template(
        "licenses/edit.html",
        active="licenses",
        item_id=item_id,
        license=license_row,
    )
