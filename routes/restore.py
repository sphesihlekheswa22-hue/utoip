"""Restore — entry into workflow-backed restore requests."""
from flask import Blueprint, redirect, url_for

bp = Blueprint("restore", __name__, url_prefix="/restore")


@bp.get("/")
def index():
    return redirect(url_for("workflows.index"))


@bp.get("/create")
def create():
    return redirect(url_for("workflows.restore_request"))


@bp.get("/<int:item_id>")
def details(item_id):
    return redirect(url_for("workflows.details", item_id=item_id))


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("workflows.details", item_id=item_id))
