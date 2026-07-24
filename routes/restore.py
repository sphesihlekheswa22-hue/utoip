"""Restore — redirects into Backup & Restore hub."""
from flask import Blueprint, redirect, url_for

bp = Blueprint("restore", __name__, url_prefix="/restore")


@bp.get("/")
def index():
    return redirect(url_for("backup.index", tab="restore"))


@bp.get("/create")
def create():
    return redirect(url_for("backup.index", tab="restore"))


@bp.get("/<int:item_id>")
def details(item_id):
    return redirect(url_for("backup.index", tab="restore"))


@bp.get("/<int:item_id>/history")
def history(item_id):
    return redirect(url_for("backup.index", tab="history"))
