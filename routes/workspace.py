"""My Workspace — personal OneDrive-style storage (separate from Documents & Backup Center)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.ui_rbac import is_employee_session, is_super_admin_session
from uitop.services import files_view as fv

bp = Blueprint("workspace", __name__, url_prefix="/workspace")


def _actor_id():
    return session.get("user_id")


@bp.get("/")
def index():
    uid = _actor_id()
    if not uid:
        return redirect(url_for("auth.login"))
    view = request.args.get("view", "mine")
    allowed = {"mine", "shared", "shared_by_me", "recent", "trash"}
    if view not in allowed:
        view = "mine"
    data = fv.build_workspace_payload(
        uid,
        q=(request.args.get("q") or "").strip() or None,
        category=(request.args.get("category") or "").strip() or None,
        view=view,
    )
    return render_template(
        "workspace/index.html",
        active="workspace",
        view=view,
        kpis=data["kpis"],
        payload=data,
        q=data.get("q") or "",
        category=data.get("category") or "",
        is_employee=is_employee_session(),
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = fv.build_detail_payload(item_id)
    if not detail:
        abort(404)
    f = detail["file"]
    if f.get("kind") != "workspace":
        return redirect(url_for("documents.details", item_id=item_id))
    row = fv.get_file_or_none(item_id)
    if not fv.user_can_access_file(
        row, _actor_id(), is_super_admin=is_super_admin_session()
    ):
        flash("That file is private to another user.", "error")
        return redirect(url_for("workspace.index"))
    return render_template(
        "workspace/details.html",
        active="workspace",
        item_id=item_id,
        detail=detail,
        file=detail["file"],
        view=request.args.get("view", "overview"),
    )


@bp.post("/upload")
def upload():
    upload_file = request.files.get("file")
    if not upload_file or not upload_file.filename:
        flash("Choose a file to upload.", "error")
        return redirect(request.referrer or url_for("workspace.index"))
    try:
        f = fv.create_file_from_upload(
            upload_file,
            category=request.form.get("category") or "My Documents",
            description=request.form.get("description") or request.form.get("notes"),
            tags=request.form.get("tags"),
            is_shared=bool(request.form.get("shared")),
            actor_id=_actor_id(),
            note=request.form.get("version_note") or "Uploaded to My Workspace",
            kind="workspace",
            status="published",
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("workspace.index"))
    flash(f"“{f.name}” saved in My Workspace.", "success")
    return redirect(url_for("workspace.details", item_id=f.id))


@bp.post("/<int:item_id>/share")
def toggle_share(item_id):
    row = fv.get_file_or_none(item_id)
    if not row or row.kind != "workspace":
        abort(404)
    if row.owner_user_id != _actor_id() and not is_super_admin_session():
        flash("Only the owner can share this file.", "error")
        return redirect(url_for("workspace.details", item_id=item_id))
    row.is_shared = not bool(row.is_shared)
    from uitop.extensions import db

    db.session.commit()
    flash("Sharing updated." if row.is_shared else "File is private again.", "success")
    return redirect(url_for("workspace.details", item_id=item_id))


@bp.post("/<int:item_id>/version")
def new_version(item_id):
    row = fv.get_file_or_none(item_id)
    if not row or row.kind != "workspace":
        abort(404)
    if not fv.user_can_access_file(row, _actor_id(), is_super_admin=is_super_admin_session()):
        flash("That file is private.", "error")
        return redirect(url_for("workspace.index"))
    upload_file = request.files.get("file")
    try:
        f = fv.add_new_version(
            item_id,
            upload_file,
            note=request.form.get("version_note"),
            actor_id=_actor_id(),
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("workspace.details", item_id=item_id, view="versions"))
    flash(f"Version {f.version_label or f.version} saved.", "success")
    return redirect(url_for("workspace.details", item_id=item_id, view="versions"))


@bp.get("/create")
def create():
    return redirect(url_for("workspace.index") + "#upload")
