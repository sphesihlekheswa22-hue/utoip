"""Inventory read stubs."""
from flask import Blueprint

from uitop.core.decorators import permission_required
from uitop.core.permissions import COMPUTERS_READ, NETWORK_READ, PRINTERS_READ, SERVERS_READ
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.schemas import success

bp = Blueprint("inventory", __name__)


@bp.get("/computers")
@permission_required(COMPUTERS_READ)
def list_computers():
    rows = Computer.query.order_by(Computer.hostname).all()
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})


@bp.get("/servers")
@permission_required(SERVERS_READ)
def list_servers():
    rows = Server.query.order_by(Server.hostname).all()
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})


@bp.get("/network/devices")
@permission_required(NETWORK_READ)
def list_network_devices():
    rows = NetworkDevice.query.order_by(NetworkDevice.hostname).all()
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})


@bp.get("/printers")
@permission_required(PRINTERS_READ)
def list_printers():
    rows = Printer.query.order_by(Printer.name).all()
    return success([r.to_dict() for r in rows], meta={"count": len(rows)})
