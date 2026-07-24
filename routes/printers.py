"""Printers module — live DB inventory."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from uitop.services import inventory_view as inv

bp = Blueprint("printers", __name__, url_prefix="/printers")


@bp.get("/")
def index():
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else inv.list_printers_for_ui()
    return render_template(
        "printers/index.html",
        active="printers",
        printers=rows,
        kpis=inv.printer_kpis(rows),
        empty=empty_flag or not rows,
    )


@bp.get("/discover")
def discover():
    return render_template("printers/discover.html", active="printers")


@bp.get("/create")
def create():
    return redirect(url_for("printers.discover"))


@bp.get("/<int:item_id>")
def details(item_id):
    from uitop.models.inventory import Printer

    row = Printer.query.get(item_id)
    if row is None:
        abort(404)
    printer = inv.serialize_printer(row)
    tab = request.args.get("tab", "overview")
    return render_template(
        "printers/details.html",
        active="printers",
        printer=printer,
        item_id=item_id,
        initial_tab=tab,
    )


@bp.get("/<int:item_id>/<page>")
def printer_page(item_id, page):
    return redirect(url_for("printers.details", item_id=item_id, tab="overview"))
