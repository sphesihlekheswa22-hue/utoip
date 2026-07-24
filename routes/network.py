"""Network devices — live DB inventory."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from uitop.services import inventory_view as inv

bp = Blueprint("network", __name__, url_prefix="/network")


@bp.get("/")
def index():
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else inv.list_network_for_ui()
    return render_template(
        "network/index.html",
        active="network",
        devices=rows,
        kpis=inv.network_kpis(rows),
        empty=empty_flag or not rows,
    )


@bp.get("/scan")
def scan():
    return render_template("network/scan.html", active="network")


@bp.get("/snmp")
def snmp():
    return render_template("network/snmp.html", active="network")


@bp.get("/create")
def create():
    return redirect(url_for("network.scan"))


@bp.get("/<int:item_id>")
def details(item_id):
    from uitop.models.inventory import NetworkDevice

    row = NetworkDevice.query.get(item_id)
    if row is None:
        abort(404)
    device = inv.serialize_network_device(row)
    tab = request.args.get("tab", "overview")
    return render_template(
        "network/details.html",
        active="network",
        device=device,
        item_id=item_id,
        initial_tab=tab,
    )


@bp.get("/<int:item_id>/<page>")
def device_page(item_id, page):
    return redirect(url_for("network.details", item_id=item_id, tab="overview"))
