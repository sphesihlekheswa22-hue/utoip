"""Computers module — live DB + agent telemetry UI."""
from __future__ import annotations

import socket
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from uitop.models.auth import AgentEnrollmentToken
from uitop.services import agents as agents_service
from uitop.services import computers_view as computers_svc
from uitop.services import pairing as pairing_svc

bp = Blueprint("computers", __name__, url_prefix="/computers")

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
_DIST_AGENT = Path(__file__).resolve().parent.parent / "dist" / "UITOP-Agent.exe"


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _public_base_url() -> str:
    """Prefer LAN URL so other PCs can reach UITOP (not 127.0.0.1)."""
    host = (request.host or "").split(":")[0]
    port = request.environ.get("SERVER_PORT") or "5500"
    if host in {"127.0.0.1", "localhost", "::1"}:
        return f"http://{_lan_ip()}:{port}"
    return request.url_root.rstrip("/")


@bp.get("/")
def index():
    from uitop.core.ui_rbac import is_employee_session

    if is_employee_session():
        return redirect(url_for("employee.devices"))
    empty_flag = request.args.get("empty") == "1"
    rows = [] if empty_flag else computers_svc.list_computers_for_ui()
    departments = computers_svc.department_names()
    return render_template(
        "computers/index.html",
        active="computers",
        computers=rows,
        kpis=computers_svc.computer_kpis(rows),
        empty=empty_flag or not rows,
        departments=departments,
    )


@bp.get("/install-agent")
def install_agent():
    tokens = (
        AgentEnrollmentToken.query.order_by(AgentEnrollmentToken.created_at.desc()).limit(10).all()
    )
    lan_url = _public_base_url()
    pairing = pairing_svc.get_active_pairing_code()
    agent_built = _DIST_AGENT.is_file()
    flash_code = session.pop("pairing_code", None)
    flash_expires = session.pop("pairing_expires", None)
    if flash_code:
        pairing = {"code": flash_code, "expires_at": flash_expires, "expires_in_seconds": 900}
    return render_template(
        "computers/install-agent.html",
        active="computers",
        enrollment_tokens=[t.to_dict() for t in tokens],
        raw_token=session.pop("enrollment_token_raw", None),
        server_url=lan_url,
        local_url=request.url_root.rstrip("/"),
        pairing=pairing,
        agent_built=agent_built,
    )


@bp.post("/install-agent/pairing")
def create_pairing_code():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))

    label = (request.form.get("label") or "Add device").strip()
    result = pairing_svc.create_pairing_code(created_by_id=user_id, label=label)
    session["pairing_code"] = result["code"]
    session["pairing_expires"] = result["expires_at"]
    flash(f"Pairing code {result['code']} — valid for 15 minutes.", "success")
    return redirect(url_for("computers.install_agent"))


@bp.get("/agent/download")
def download_agent_exe():
    """Public download — standalone agent (no Python on target PC)."""
    if not _DIST_AGENT.is_file():
        flash("Agent installer not built yet. Ask IT to run: powershell -File tools/build_agent.ps1", "error")
        from uitop.core.ui_rbac import is_employee_session

        if is_employee_session():
            return redirect(url_for("employee.connect"))
        return redirect(url_for("computers.install_agent"))
    return send_from_directory(
        _DIST_AGENT.parent,
        _DIST_AGENT.name,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name="UITOP-Agent.exe",
    )


@bp.post("/install-agent/token")
def create_enrollment_token():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))

    label = (request.form.get("label") or "Computers enroll").strip()
    token, raw = agents_service.create_enrollment_token(
        label=label,
        created_by_id=user_id,
        expires_hours=int(request.form.get("expires_hours") or 168),
        max_uses=int(request.form.get("max_uses") or 50),
    )
    session["enrollment_token_raw"] = raw
    flash(f"Enrollment token created ({token.token_prefix}…). Copy it now — it won't be shown again.", "success")
    return redirect(url_for("computers.install_agent"))


@bp.get("/agent/local_agent.py")
def download_agent_script():
    """Public download — other PCs pull the agent without logging in."""
    if not (_AGENTS_DIR / "local_agent.py").is_file():
        abort(404)
    return send_from_directory(
        _AGENTS_DIR,
        "local_agent.py",
        mimetype="text/x-python",
        as_attachment=True,
        download_name="local_agent.py",
    )


@bp.get("/agent/install.ps1")
def download_install_ps1():
    """Public PowerShell installer (server URL baked from request host)."""
    path = _AGENTS_DIR / "install.ps1"
    if not path.is_file():
        abort(404)
    # Serve as-is; caller passes -Server / -Token
    return Response(
        path.read_text(encoding="utf-8"),
        mimetype="text/plain",
        headers={"Content-Disposition": "inline; filename=install.ps1"},
    )


@bp.get("/scan-network")
def scan_network():
    return render_template("computers/scan-network.html", active="computers")


@bp.get("/create")
def create():
    """Legacy URL — redirect to Install Agent."""
    return redirect(url_for("computers.install_agent"))


@bp.get("/<int:item_id>")
def details(item_id):
    computer = computers_svc.get_computer_or_none(item_id)
    if computer is None:
        abort(404)
    device = computers_svc.serialize_computer(computer)
    tab = request.args.get("tab", "overview")
    from uitop.services import agent_commands as cmd_svc
    from uitop.services import files_view as files_svc

    linked_files = files_svc.list_files_for_object("computer", item_id)
    recent_cmds = [c.to_dict() for c in cmd_svc.list_commands_for_computer(item_id, limit=15)]
    return render_template(
        "computers/details.html",
        active="computers",
        device=device,
        item_id=item_id,
        initial_tab=tab,
        perf_series=computers_svc.performance_series(item_id),
        agent_events=computers_svc.recent_events(item_id),
        agent_alerts=computers_svc.recent_alerts(item_id),
        linked_files=linked_files,
        recent_commands=recent_cmds,
        has_agent=bool(computer.agent_id),
    )


@bp.post("/<int:item_id>/remote/<command>")
def remote_command(item_id, command):
    """Queue a real remote action for the enrolled agent (or WoL on server)."""
    from flask import jsonify

    from uitop.core.errors import APIError
    from uitop.services import agent_commands as cmd_svc

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Sign in required"}), 401
    try:
        row = cmd_svc.queue_command(
            computer_id=item_id,
            command=command,
            created_by_id=user_id,
        )
    except APIError as exc:
        return jsonify({"error": exc.message}), getattr(exc, "status_code", 400)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    label = cmd_svc.COMMAND_LABELS.get(row.command, row.command)
    if row.status == "completed":
        msg = f"{label}: {row.result or 'done'}"
    elif row.status == "failed":
        msg = f"{label} failed: {row.result}"
    else:
        msg = f"{label} queued — agent will run it within ~30s"
    return jsonify({"ok": True, "message": msg, "command": row.to_dict()})


@bp.get("/<int:item_id>/remote")
def remote_command_list(item_id):
    from flask import jsonify

    from uitop.services import agent_commands as cmd_svc

    rows = cmd_svc.list_commands_for_computer(item_id, limit=20)
    return jsonify({"commands": [r.to_dict() for r in rows]})


@bp.get("/<int:item_id>/edit")
def edit(item_id):
    return redirect(url_for("computers.details", item_id=item_id, tab="overview"))


@bp.get("/<int:item_id>/<page>")
def device_page(item_id, page):
    """Map old sub-routes into details tabs."""
    mapping = {
        "performance": "performance",
        "software": "software",
        "services": "services",
        "event-logs": "events",
        "network": "network",
        "processes": "processes",
        "remote-access": "remote",
        "history": "timeline",
        "delete": "overview",
    }
    tab = mapping.get(page, "overview")
    return redirect(url_for("computers.details", item_id=item_id, tab=tab))
