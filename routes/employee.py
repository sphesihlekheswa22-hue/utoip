"""Employee self-service portal — municipal staff (non-IT)."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from uitop.core.ui_rbac import is_employee_session
from uitop.services import employee_view as emp
from uitop.services import pairing as pairing_svc

bp = Blueprint("employee", __name__, url_prefix="/employee")

_DIST_AGENT = Path(__file__).resolve().parent.parent / "dist" / "UITOP-Agent.exe"


def _public_base_url() -> str:
    """Prefer LAN-reachable URL when request host is localhost."""
    root = request.url_root.rstrip("/")
    host = (request.host or "").split(":")[0].lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        try:
            import socket

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            port = request.environ.get("SERVER_PORT") or "5500"
            return f"http://{ip}:{port}"
        except OSError:
            pass
    return root


@bp.get("/")
def index():
    data = emp.build_employee_home()
    return render_template(
        "employee/index.html",
        active="employee",
        home=data,
        is_employee=is_employee_session(),
    )


@bp.get("/connect")
def connect():
    """Simple no-Python PC enrollment for employees."""
    pairing = None
    flash_code = session.pop("emp_pairing_code", None)
    flash_expires = session.pop("emp_pairing_expires", None)
    if flash_code:
        pairing = {"code": flash_code, "expires_at": flash_expires, "expires_in_seconds": 900}
    else:
        pairing = pairing_svc.get_active_pairing_code()
    return render_template(
        "employee/connect.html",
        active="connect-pc",
        pairing=pairing,
        server_url=_public_base_url(),
        agent_built=_DIST_AGENT.is_file(),
        is_employee=is_employee_session(),
    )


@bp.post("/connect/pair")
def connect_pair():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    try:
        result = pairing_svc.create_pairing_code(
            created_by_id=user_id,
            label=f"Employee pair · user {user_id}",
        )
        session["emp_pairing_code"] = result["code"]
        session["emp_pairing_expires"] = result["expires_at"]
        flash(f"Your code is {result['code']} — valid for 15 minutes.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(str(getattr(exc, "message", None) or exc), "error")
    return redirect(url_for("employee.connect"))


@bp.get("/devices")
def devices():
    data = emp.list_my_devices()
    return render_template(
        "employee/devices.html",
        active="my-devices",
        devices=data,
        agent_built=_DIST_AGENT.is_file(),
        is_employee=is_employee_session(),
    )


@bp.get("/tickets")
def tickets():
    status = (request.args.get("status") or "").strip() or None
    rows = emp.list_my_tickets(status=status)
    return render_template(
        "employee/tickets.html",
        active="my-tickets",
        tickets=rows,
        status=status or "",
        is_employee=is_employee_session(),
    )


@bp.post("/devices/<int:asset_id>/report")
def report_device(asset_id: int):
    """Shortcut: start a helpdesk ticket about a device problem."""
    user_id = session.get("user_id")
    devices = emp.list_my_devices(user_id)
    asset = next((a for a in devices["assets"] if a["id"] == asset_id), None)
    subject = f"Device problem: {asset['name'] if asset else f'Asset #{asset_id}'}"
    return redirect(
        url_for(
            "helpdesk.create",
            subject=subject,
            link_type="asset" if asset else "none",
            link_id=asset_id if asset else None,
        )
    )
