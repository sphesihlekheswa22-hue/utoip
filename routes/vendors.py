"""Vendors module — supplier hub UI (mock data, archive-friendly)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from uitop.services import vendors_view as ven

bp = Blueprint("vendors", __name__, url_prefix="/vendors")


@bp.get("/")
def index():
    data = ven.build_module_payload()
    return render_template(
        "vendors/index.html",
        active="vendors",
        kpis=data["kpis"],
        payload=data,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = ven.build_detail_payload(item_id)
    if not detail:
        abort(404)
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("vendor", item_id)
    return render_template(
        "vendors/details.html",
        active="vendors",
        item_id=item_id,
        detail=detail,
        vendor=detail["vendor"],
        view=request.args.get("view", "overview"),
        linked_files=linked_files,
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        flash("Vendor saved (demo — backend wiring next).", "success")
        return redirect(url_for("vendors.index"))
    return render_template(
        "vendors/create.html",
        active="vendors",
        categories=ven.CATEGORIES,
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    vendor = ven.get_vendor(item_id)
    if not vendor:
        abort(404)
    if request.method == "POST":
        flash(f"{vendor['name']} updated (demo).", "success")
        return redirect(url_for("vendors.details", item_id=item_id))
    return render_template(
        "vendors/edit.html",
        active="vendors",
        item_id=item_id,
        vendor=vendor,
        categories=ven.CATEGORIES,
    )


@bp.post("/<int:item_id>/archive")
def archive(item_id):
    vendor = ven.get_vendor(item_id)
    if not vendor:
        abort(404)
    flash(f"{vendor['name']} archived (demo — not deleted).", "success")
    return redirect(url_for("vendors.index"))
