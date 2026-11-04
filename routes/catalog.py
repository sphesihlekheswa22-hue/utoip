"""Request Catalog — ServiceNow-style employee service offerings."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.core.ui_rbac import is_employee_session
from uitop.services import catalog as cat
from uitop.services import workflow as wf

bp = Blueprint("catalog", __name__, url_prefix="/catalog")


def _uid():
    return session.get("user_id")


@bp.get("/")
def index():
    wf.ensure_workflow_definitions()
    category = request.args.get("category") or None
    q = request.args.get("q") or None
    items = cat.list_catalog(category=category, q=q)
    return render_template(
        "catalog/index.html",
        active="catalog",
        items=items,
        categories=cat.catalog_categories(),
        category=category,
        q=q or "",
        is_employee=is_employee_session(),
    )


@bp.route("/<key>/request", methods=["GET", "POST"])
def request_item(key):
    uid = _uid()
    if not uid:
        return redirect(url_for("auth.login"))

    item = cat.get_catalog_item(key)
    if not item:
        flash("Unknown catalog item.", "error")
        return redirect(url_for("catalog.index"))

    if item.get("redirect"):
        return redirect(url_for(item["redirect"]))

    if request.method == "POST":
        try:
            inst = wf.start_catalog_request(
                catalog_key=key,
                requester_id=uid,
                form=request.form.to_dict(),
                priority=request.form.get("priority"),
            )
            flash(f"Request {inst.number} submitted.", "success")
            return redirect(url_for("workflows.details", item_id=inst.id))
        except APIError as err:
            flash(err.message, "error")

    return render_template(
        "catalog/request.html",
        active="catalog",
        item=item,
        is_employee=is_employee_session(),
    )
