"""Servers module — live DB inventory."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from uitop.services import inventory_view as inv

bp = Blueprint("servers", __name__, url_prefix="/servers")


@bp.get("/")
def index():
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else inv.list_servers_for_ui()
    return render_template(
        "servers/index.html",
        active="servers",
        servers=rows,
        kpis=inv.server_kpis(rows),
        empty=empty_flag or not rows,
    )


@bp.get("/discover")
def discover():
    return render_template("servers/discover.html", active="servers")


@bp.get("/install-agent")
def install_agent():
    return render_template("servers/install-agent.html", active="servers")


@bp.get("/create")
def create():
    return redirect(url_for("servers.discover"))


@bp.get("/<int:item_id>")
def details(item_id):
    from uitop.models.inventory import Server

    row = Server.query.get(item_id)
    if row is None:
        abort(404)
    server = inv.serialize_server(row)
    tab = request.args.get("tab", "overview")
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("server", item_id)
    return render_template(
        "servers/details.html",
        active="servers",
        server=server,
        item_id=item_id,
        initial_tab=tab,
        linked_files=linked_files,
    )


@bp.get("/<int:item_id>/edit")
def edit(item_id):
    return redirect(url_for("servers.details", item_id=item_id))


@bp.get("/<int:item_id>/<page>")
def server_page(item_id, page):
    mapping = {
        "performance": "performance",
        "services": "services",
        "history": "timeline",
    }
    return redirect(url_for("servers.details", item_id=item_id, tab=mapping.get(page, "overview")))
