"""Backup & Restore hub — infrastructure protection UI."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from uitop.services import backup_view as bv

bp = Blueprint("backup", __name__, url_prefix="/backup")


@bp.get("/")
def index():
    tab = request.args.get("tab", "overview")
    allowed = {
        "overview",
        "jobs",
        "restore",
        "schedules",
        "storage",
        "points",
        "history",
        "policies",
    }
    if tab not in allowed:
        tab = "overview"
    data = bv.build_module_payload()
    return render_template(
        "backup/index.html",
        active="backup",
        tab=tab,
        kpis=data["kpis"],
        payload=data,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    job = bv.get_job(item_id)
    if not job:
        abort(404)
    return render_template(
        "backup/details.html",
        active="backup",
        item_id=item_id,
        job=job,
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        flash("Backup job created (demo).", "success")
        return redirect(url_for("backup.index", tab="jobs"))
    return render_template("backup/create.html", active="backup")


@bp.post("/restore")
def start_restore():
    flash("Restore job queued (demo).", "success")
    return redirect(url_for("backup.index", tab="restore"))
