"""Enterprise IT File Repository — attachments linked to UITOP objects."""
from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from uitop.services import files_view as fv

bp = Blueprint("files", __name__, url_prefix="/files")


def _actor_id():
    return session.get("user_id")


def _parse_links_from_form():
    links = []
    # Multi-link: link_type[] + link_id[] or single link_type/link_id
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
    # Convenience: pre-bound object from entity pages
    bound_type = (request.form.get("bound_type") or "").strip()
    bound_id = request.form.get("bound_id", type=int)
    if bound_type and bound_id:
        links.append((bound_type, bound_id))
    # Dedupe
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
    q = (request.args.get("q") or "").strip() or None
    category = (request.args.get("category") or "").strip() or None
    data = fv.build_module_payload(q=q, category=category)
    return render_template(
        "files/index.html",
        active="files",
        kpis=data["kpis"],
        payload=data,
        q=q or "",
        category=category or "",
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = fv.build_detail_payload(item_id)
    if not detail:
        abort(404)
    return render_template(
        "files/details.html",
        active="files",
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
        return redirect(request.referrer or url_for("files.index"))
    try:
        f = fv.create_file_from_upload(
            upload_file,
            category=request.form.get("category") or "Documentation",
            description=request.form.get("description") or request.form.get("notes"),
            tags=request.form.get("tags"),
            is_shared=bool(request.form.get("shared")),
            actor_id=_actor_id(),
            links=_parse_links_from_form(),
            note=request.form.get("version_note") or "Initial upload",
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("files.index"))
    flash(f"Stored {f.name} in the IT repository and linked to platform objects.", "success")
    next_url = request.form.get("next") or url_for("files.details", item_id=f.id)
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
        return redirect(url_for("files.details", item_id=item_id, view="versions"))
    flash(f"Version {f.version} saved.", "success")
    return redirect(url_for("files.details", item_id=item_id, view="versions"))


@bp.post("/<int:item_id>/link")
def add_link(item_id):
    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    link_type = (request.form.get("link_type") or "").strip()
    link_id = request.form.get("link_id", type=int)
    if not link_type or not link_id:
        flash("Select an object to link.", "error")
        return redirect(url_for("files.details", item_id=item_id, view="links"))
    fv.add_link(f, link_type, link_id, actor_id=_actor_id())
    from uitop.extensions import db

    db.session.commit()
    flash("Object linked.", "success")
    return redirect(url_for("files.details", item_id=item_id, view="links"))


@bp.get("/<int:item_id>/download")
def download(item_id):
    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    path = fv.absolute_path(f)
    if path is None:
        flash("No stored blob for this demo entry (metadata only).", "error")
        return redirect(url_for("files.details", item_id=item_id))
    fv.log_activity(f.id, "downloaded", f"Downloaded {f.name}", _actor_id())
    from uitop.extensions import db

    db.session.commit()
    return send_file(path, as_attachment=True, download_name=f.original_name or f.name)


@bp.get("/<int:item_id>/preview")
def preview(item_id):
    f = fv.get_file_or_none(item_id)
    if not f:
        abort(404)
    path = fv.absolute_path(f)
    if path is None:
        abort(404)
    fv.log_activity(f.id, "previewed", f"Previewed {f.name}", _actor_id())
    from uitop.extensions import db

    db.session.commit()
    return send_file(path, as_attachment=False, download_name=f.original_name or f.name)
