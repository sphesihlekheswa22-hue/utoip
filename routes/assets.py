"""Assets module — lifecycle / ownership over discovered inventory."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.models.assets import Asset, AssetAssignment, AssetCategory, AssetRequest
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.user import User
from uitop.services import assets as assets_svc

bp = Blueprint("assets", __name__, url_prefix="/assets")


@bp.get("/")
def index():
    from uitop.core.ui_rbac import is_employee_session

    if is_employee_session():
        return redirect(url_for("employee.devices"))
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else assets_svc.list_assets()
    return render_template(
        "assets/index.html",
        active="assets",
        assets=rows,
        kpis=assets_svc.asset_kpis(rows),
        empty=empty_flag or not rows,
        categories=AssetCategory.query.order_by(AssetCategory.name).all(),
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    """Register a non-IT / store asset (not for PCs — use Link or agents)."""
    categories = AssetCategory.query.order_by(AssetCategory.name).all()
    if request.method == "POST":
        try:
            asset = assets_svc.create_non_it_asset(
                name=request.form.get("name"),
                category_id=request.form.get("category_id", type=int),
                location=request.form.get("location"),
                serial_number=request.form.get("serial_number"),
                notes=request.form.get("notes"),
                asset_tag=request.form.get("asset_tag") or None,
                actor_id=session.get("user_id"),
            )
            flash(f"Asset {asset.asset_tag} registered in store.", "success")
            return redirect(url_for("assets.details", item_id=asset.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "assets/create.html",
        active="assets",
        categories=categories,
    )


@bp.get("/link")
def link_page():
    """Link an asset to a discovered device, or create+link."""
    unlinked_computers = []
    for c in Computer.query.order_by(Computer.hostname).all():
        if not Asset.query.filter_by(linked_type="computer", linked_id=c.id).first():
            unlinked_computers.append(c)
    return render_template(
        "assets/link.html",
        active="assets",
        computers=unlinked_computers,
        servers=Server.query.order_by(Server.hostname).all(),
        network=NetworkDevice.query.order_by(NetworkDevice.hostname).all(),
        printers=Printer.query.order_by(Printer.name).all(),
        assets=[a for a in Asset.query.order_by(Asset.asset_tag).all() if a.linked_type in (None, "none") or not a.linked_id],
        categories=AssetCategory.query.order_by(AssetCategory.name).all(),
    )


@bp.post("/link")
def link_submit():
    linked_type = request.form.get("linked_type")
    linked_id = request.form.get("linked_id", type=int)
    asset_id = request.form.get("asset_id", type=int)
    actor_id = session.get("user_id")
    try:
        if asset_id:
            asset = assets_svc.link_asset_to_device(
                asset_id, linked_type=linked_type, linked_id=linked_id, actor_id=actor_id
            )
        else:
            # Create then link
            name = request.form.get("name") or f"{linked_type}-{linked_id}"
            asset = assets_svc.create_non_it_asset(
                name=name,
                category_id=request.form.get("category_id", type=int),
                location=None,
                serial_number=None,
                notes="Linked from discovered inventory",
                actor_id=actor_id,
            )
            asset = assets_svc.link_asset_to_device(
                asset.id, linked_type=linked_type, linked_id=linked_id, actor_id=actor_id
            )
        flash(f"Linked {asset.asset_tag} to {linked_type} #{linked_id}.", "success")
        return redirect(url_for("assets.details", item_id=asset.id))
    except APIError as err:
        flash(err.message, "error")
        return redirect(url_for("assets.link_page"))


@bp.route("/request", methods=["GET", "POST"])
def request_asset():
    categories = AssetCategory.query.order_by(AssetCategory.name).all()
    if request.method == "POST":
        user_id = session.get("user_id")
        if not user_id:
            flash("Sign in required.", "error")
            return redirect(url_for("auth.login"))
        try:
            req = assets_svc.create_request(
                requester_id=user_id,
                title=request.form.get("title"),
                category_id=request.form.get("category_id", type=int),
                justification=request.form.get("justification"),
            )
            flash(f"Request #{req.id} submitted.", "success")
            return redirect(url_for("assets.requests_list"))
        except APIError as err:
            flash(err.message, "error")
    return render_template("assets/request.html", active="assets", categories=categories)


@bp.get("/requests")
def requests_list():
    rows = AssetRequest.query.order_by(AssetRequest.created_at.desc()).limit(100).all()
    return render_template(
        "assets/requests.html",
        active="assets",
        requests=[r.to_dict() for r in rows],
        item_id=0,
    )


@bp.get("/categories")
def categories_list():
    cats = AssetCategory.query.order_by(AssetCategory.name).all()
    return render_template(
        "assets/categories.html",
        active="assets",
        categories=[c.to_dict() for c in cats],
        item_id=0,
    )


@bp.get("/<int:item_id>")
def details(item_id):
    try:
        asset = assets_svc.get_asset_or_404(item_id)
    except APIError:
        abort(404)
    data = assets_svc.serialize_asset(asset)
    history = [
        a.to_dict()
        for a in AssetAssignment.query.filter_by(asset_id=asset.id)
        .order_by(AssetAssignment.assigned_at.desc())
        .limit(20)
    ]
    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("asset", item_id)
    return render_template(
        "assets/details.html",
        active="assets",
        asset=data,
        item_id=item_id,
        history=history,
        users=users,
        linked_files=linked_files,
    )


@bp.post("/<int:item_id>/assign")
def assign(item_id):
    try:
        assets_svc.assign_asset(
            item_id,
            assignee_name=request.form.get("assignee_name"),
            user_id=request.form.get("user_id", type=int) or None,
            department_id=None,
            notes=request.form.get("notes"),
            actor_id=session.get("user_id"),
        )
        flash("Asset assigned.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("assets.details", item_id=item_id))


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    try:
        asset = assets_svc.get_asset_or_404(item_id)
    except APIError:
        abort(404)
    categories = AssetCategory.query.order_by(AssetCategory.name).all()
    if request.method == "POST":
        asset.name = request.form.get("name") or asset.name
        asset.location = request.form.get("location")
        asset.serial_number = request.form.get("serial_number")
        asset.notes = request.form.get("notes")
        cat_id = request.form.get("category_id", type=int)
        if cat_id:
            asset.category_id = cat_id
        status = request.form.get("status")
        if status:
            asset.status = status
        from uitop.extensions import db

        db.session.commit()
        flash("Asset updated.", "success")
        return redirect(url_for("assets.details", item_id=item_id))
    return render_template(
        "assets/edit.html",
        active="assets",
        asset=assets_svc.serialize_asset(asset),
        item_id=item_id,
        categories=categories,
    )


@bp.get("/<int:item_id>/assignments")
def assignments(item_id):
    return redirect(url_for("assets.details", item_id=item_id) + "#assignments")


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("assets.details", item_id=item_id) + "#history")


@bp.get("/<int:item_id>/categories")
def categories(item_id):
    return redirect(url_for("assets.categories_list"))


@bp.get("/<int:item_id>/vendors")
def vendors(item_id):
    return redirect(url_for("assets.index"))


@bp.get("/<int:item_id>/requests")
def requests(item_id):
    return redirect(url_for("assets.requests_list"))
