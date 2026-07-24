"""Software Management module — enterprise lifecycle UI (mock data)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from uitop.services import software_view as sw

bp = Blueprint("software", __name__, url_prefix="/software")


@bp.get("/")
def index():
    tab = request.args.get("tab", "catalog")
    allowed = {"catalog", "installed", "deployment", "updates", "requests", "blacklist", "licenses"}
    if tab not in allowed:
        tab = "catalog"
    data = sw.build_module_payload()
    return render_template(
        "software/index.html",
        active="software",
        tab=tab,
        kpis=data["kpis"],
        payload=data,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = sw.build_detail_payload(item_id)
    if not detail:
        abort(404)
    sub = request.args.get("view", "overview")
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("software", item_id)
    return render_template(
        "software/details.html",
        active="software",
        item_id=item_id,
        view=sub,
        detail=detail,
        software=detail["software"],
        linked_files=linked_files,
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        flash("Catalog entry saved (demo — backend wiring next).", "success")
        return redirect(url_for("software.index", tab="catalog"))
    return render_template("software/create.html", active="software")


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    software = sw.get_software(item_id)
    if not software:
        abort(404)
    if request.method == "POST":
        flash(f"{software['name']} updated (demo).", "success")
        return redirect(url_for("software.details", item_id=item_id))
    return render_template(
        "software/edit.html",
        active="software",
        item_id=item_id,
        software=software,
    )


@bp.post("/requests/<int:req_id>/<action>")
def request_action(req_id, action):
    if action not in {"approve", "deny"}:
        abort(404)
    flash(f"Request #{req_id} marked {action}d (demo).", "success")
    return redirect(url_for("software.index", tab="requests"))
