"""File/attachment API endpoints — uploads redirect into Documents DMS."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, request, send_file, session, url_for

from uitop.services import files_view as fv

bp = Blueprint("files", __name__, url_prefix="/files")


def _actor_id():
    return session.get("user_id")


def _parse_links_from_form():
    links = []
    types = request.form.getlist("link_type")
    ids = request.form.getlist("link_id")
    if types and ids and len(types) == len(ids):
        for t, i in zip(types, ids):
            if t and i and str(i).isdigit():
                links.append((t, int(i)))
    else:
        t = (request.form.get("link_type") or "").strip()
        i = request.form.get("link_id", type=int)
        if t and i:
            links.append((t, i))
    bound_type = (request.form.get("bound_type") or "").strip()
    bound_id = request.form.get("bound_id", type=int)
    if bound_type and bound_id:
        links.append((bound_type, bound_id))
    seen = set()
    out = []
    for t, i in links:
        key = (t, i)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


@bp.get("/")
def index():
    return redirect(url_for("documents.index"))


@bp.get("/<int:item_id>")
def details(item_id):
    return redirect(url_for("documents.details", item_id=item_id, view=request.args.get("view")))


@bp.post("/upload")
def upload():
    """Entity attachment uploads (and legacy callers)."""
    upload_file = request.files.get("file")
    if not upload_file or not upload_file.filename:
        flash("Choose a file to upload.", "error")
        return redirect(request.referrer or url_for("documents.index"))
    kind = (request.form.get("kind") or "attachment").strip()
    # Entity bound uploads default to attachments
    if request.form.get("bound_type") and kind == "document" and not request.form.get("as_document"):
        kind = "attachment"
    try:
        f = fv.create_file_from_upload(
            upload_file,
            category=request.form.get("category") or "Other",
            description=request.form.get("description") or request.form.get("notes"),
            tags=request.form.get("tags"),
            is_shared=bool(request.form.get("shared")),
            actor_id=_actor_id(),
            links=_parse_links_from_form(),
            note=request.form.get("version_note") or "Initial upload",
            kind=kind,
            status=request.form.get("status") or ("published" if kind == "attachment" else "draft"),
            owner_name=request.form.get("owner_name"),
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("documents.index"))
    flash(f"Attached {f.name}.", "success")
    next_url = request.form.get("next") or url_for("documents.details", item_id=f.id)
    return redirect(next_url)


@bp.post("/<int:item_id>/version")
def new_version(item_id):
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
        return redirect(url_for("documents.details", item_id=item_id, view="versions"))
    flash(f"Version {f.version_label or f.version} saved.", "success")
    return redirect(url_for("documents.details", item_id=item_id, view="versions"))


@bp.post("/<int:item_id>/link")
def add_link(item_id):
    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    link_type = (request.form.get("link_type") or "").strip()
    link_id = request.form.get("link_id", type=int)
    if not link_type or not link_id:
        flash("Select an object to link.", "error")
        return redirect(url_for("documents.details", item_id=item_id, view="links"))
    fv.add_link(f, link_type, link_id, actor_id=_actor_id())
    from uitop.extensions import db

    db.session.commit()
    flash("Object linked.", "success")
    return redirect(url_for("documents.details", item_id=item_id, view="links"))


@bp.get("/<int:item_id>/download")
def download(item_id):
    from uitop.core.ui_rbac import is_super_admin_session

    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    if not fv.user_can_access_file(f, _actor_id(), is_super_admin=is_super_admin_session()):
        flash("That file is private.", "error")
        return redirect(url_for("workspace.index" if f.kind == "workspace" else "documents.index"))
    path = fv.absolute_path(f)
    if path is None:
        flash("No stored blob for this entry (metadata only).", "error")
        dest = "workspace.details" if f.kind == "workspace" else "documents.details"
        return redirect(url_for(dest, item_id=item_id))
    fv.log_activity(f.id, "downloaded", f"Downloaded {f.name}", _actor_id())
    from uitop.extensions import db

    db.session.commit()
    return send_file(path, as_attachment=True, download_name=f.original_name or f.name)


@bp.get("/<int:item_id>/preview")
def preview(item_id):
    from uitop.core.ui_rbac import is_super_admin_session

    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    if not fv.user_can_access_file(f, _actor_id(), is_super_admin=is_super_admin_session()):
        abort(403)
    path = fv.absolute_path(f)
    if path is None:
        abort(404)
    fv.log_activity(f.id, "previewed", f"Previewed {f.name}", _actor_id())
    from uitop.extensions import db

    db.session.commit()
    return send_file(path, as_attachment=False, download_name=f.original_name or f.name)
