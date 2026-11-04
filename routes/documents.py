"""Documents — enterprise IT document management (DMS)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.services import files_view as fv

bp = Blueprint("documents", __name__, url_prefix="/documents")


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
    fv.migrate_legacy_backup_document_category()
    fv.repair_placeholder_document_blobs()
    from uitop.extensions import db

    db.session.commit()

    view = request.args.get("view", "dashboard")
    allowed = {"dashboard", "library", "pending", "expired", "shared", "attachments", "archive"}
    if view not in allowed:
        view = "dashboard"

    kind = "attachment" if view == "attachments" else "document"
    status = None
    if view == "pending":
        status = request.args.get("status") or None
        # pending shows draft + review
        data = fv.build_module_payload(
            q=(request.args.get("q") or "").strip() or None,
            category=(request.args.get("category") or "").strip() or None,
            kind="document",
            view=view,
        )
        data["files"] = [f for f in data["files"] if f["status"] in ("draft", "review")]
        data["documents"] = data["files"]
        data["kpis"] = fv.kpis(kind="document")
    elif view == "expired":
        data = fv.build_module_payload(
            q=(request.args.get("q") or "").strip() or None,
            category=(request.args.get("category") or "").strip() or None,
            kind="document",
            view=view,
        )
        data["files"] = [f for f in data["files"] if f.get("expired")]
        data["documents"] = data["files"]
    elif view == "shared":
        data = fv.build_module_payload(
            q=(request.args.get("q") or "").strip() or None,
            category=(request.args.get("category") or "").strip() or None,
            kind="document",
            view=view,
        )
        data["files"] = [f for f in data["files"] if f.get("shared")]
        data["documents"] = data["files"]
    elif view == "archive":
        data = fv.build_module_payload(
            q=(request.args.get("q") or "").strip() or None,
            category=(request.args.get("category") or "").strip() or None,
            kind="document",
            status="archived",
            view=view,
        )
    else:
        data = fv.build_module_payload(
            q=(request.args.get("q") or "").strip() or None,
            category=(request.args.get("category") or "").strip() or None,
            kind=kind,
            status=status,
            view=view,
        )
        # Keep live library free of archived unless Archive tab
        if view in ("dashboard", "library") and kind == "document":
            data["files"] = [f for f in data["files"] if f.get("status") != "archived"]
            data["documents"] = data["files"]

    return render_template(
        "documents/index.html",
        active="documents",
        view=view,
        kpis=data["kpis"],
        payload=data,
        q=data.get("q") or "",
        category=data.get("category") or "",
    )


@bp.get("/<int:item_id>")
def details(item_id):
    detail = fv.build_detail_payload(item_id)
    if not detail:
        abort(404)
    if detail["file"].get("kind") == "workspace":
        return redirect(url_for("workspace.details", item_id=item_id))
    return render_template(
        "documents/details.html",
        active="documents",
        item_id=item_id,
        detail=detail,
        file=detail["file"],
        view=request.args.get("view", "overview"),
    )


@bp.post("/upload")
def upload():
    upload_file = request.files.get("file")
    if not upload_file or not upload_file.filename:
        flash("Choose a document to upload.", "error")
        return redirect(request.referrer or url_for("documents.index"))
    kind = (request.form.get("kind") or "document").strip()
    try:
        f = fv.create_file_from_upload(
            upload_file,
            category=request.form.get("category") or "Manuals",
            description=request.form.get("description") or request.form.get("notes"),
            tags=request.form.get("tags"),
            is_shared=bool(request.form.get("shared")),
            actor_id=_actor_id(),
            links=_parse_links_from_form(),
            note=request.form.get("version_note") or "Initial upload",
            kind=kind,
            status=request.form.get("status") or ("draft" if kind == "document" else "published"),
            owner_name=request.form.get("owner_name"),
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("documents.index"))
    label = "Document" if f.kind == "document" else "Attachment"
    flash(f"{label} “{f.name}” stored in UITOP.", "success")
    next_url = request.form.get("next") or url_for("documents.details", item_id=f.id)
    return redirect(next_url)


@bp.post("/<int:item_id>/status")
def set_status(item_id):
    try:
        fv.transition_status(
            item_id,
            request.form.get("status"),
            note=request.form.get("note"),
            actor_id=_actor_id(),
        )
        flash("Document status updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("documents.details", item_id=item_id, view="approvals"))


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


@bp.post("/<int:item_id>/rollback")
def rollback(item_id):
    try:
        ver = request.form.get("version", type=int)
        fv.rollback_version(item_id, ver, actor_id=_actor_id())
        flash(f"Rolled back to version {ver}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
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


@bp.get("/create")
def create():
    return redirect(url_for("documents.index", view="library") + "#upload")
