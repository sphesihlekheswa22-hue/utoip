"""Network devices — live DB inventory + SNMP profiles + site connector."""
from __future__ import annotations

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

from uitop.core.errors import APIError
from uitop.core.ui_rbac import has_perm
from uitop.services import agents as agents_service
from uitop.services import inventory_view as inv
from uitop.services import printer_snmp as prn_svc
from uitop.services import site_connectors as conn_svc

bp = Blueprint("network", __name__, url_prefix="/network")
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def _public_server_url() -> str:
    return request.url_root.rstrip("/")


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


@bp.get("/site-connector")
def site_connector():
    """Manage on-prem LAN site connectors for cloud UITOP."""
    if not has_perm("connectors:manage", "agents:manage", "network:write"):
        flash("You need connector or network manage rights.", "error")
        return redirect(url_for("network.index"))

    connectors = [c.to_dict() for c in conn_svc.list_connectors()]
    raw_token = session.pop("connector_enrollment_token", None)
    return render_template(
        "network/site_connector.html",
        active="site-connector",
        connectors=connectors,
        raw_token=raw_token,
        server_url=_public_server_url(),
    )


@bp.post("/site-connector/token")
def site_connector_token():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    if not has_perm("connectors:manage", "agents:manage"):
        flash("Not allowed to create enrollment tokens.", "error")
        return redirect(url_for("network.site_connector"))
    label = (request.form.get("label") or "Site connector").strip() or "Site connector"
    token, raw = agents_service.create_enrollment_token(
        label=label,
        created_by_id=user_id,
        expires_hours=int(request.form.get("expires_hours") or 168),
        max_uses=int(request.form.get("max_uses") or 5),
    )
    session["connector_enrollment_token"] = raw
    flash(f"Enrollment token created ({token.token_prefix}…). Copy it now — it won't be shown again.", "success")
    return redirect(url_for("network.site_connector"))


@bp.get("/site-connector/site_connector.py")
def download_site_connector_script():
    """Public download for on-prem LAN PCs."""
    if not (_AGENTS_DIR / "site_connector.py").is_file():
        abort(404)
    return send_from_directory(
        _AGENTS_DIR,
        "site_connector.py",
        mimetype="text/x-python",
        as_attachment=True,
        download_name="site_connector.py",
    )


@bp.get("/site-connector/install.ps1")
def download_site_connector_ps1():
    path = _AGENTS_DIR / "install_site_connector.ps1"
    if not path.is_file():
        abort(404)
    return Response(
        path.read_text(encoding="utf-8"),
        mimetype="text/plain",
        headers={"Content-Disposition": "inline; filename=install_site_connector.ps1"},
    )


@bp.get("/snmp")
def snmp():
    prn_svc.ensure_default_profile()
    profiles = prn_svc.list_profiles()
    return render_template(
        "network/snmp.html",
        active="network",
        profiles=[p.to_dict(include_secret=True) for p in profiles],
    )


@bp.post("/snmp")
def snmp_create():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))
    try:
        prn_svc.create_profile(
            name=request.form.get("name") or "",
            community=request.form.get("community") or "",
            version=request.form.get("version") or "v2c",
            scope=request.form.get("scope") or "",
            is_write=request.form.get("is_write") == "1",
        )
        flash("SNMP profile saved.", "success")
    except APIError as exc:
        flash(exc.message, "error")
    return redirect(url_for("network.snmp"))


@bp.post("/snmp/<int:profile_id>/delete")
def snmp_delete(profile_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))
    try:
        prn_svc.delete_profile(profile_id)
        flash("SNMP profile removed.", "success")
    except APIError as exc:
        flash(exc.message, "error")
    return redirect(url_for("network.snmp"))


@bp.post("/snmp/<int:profile_id>/test")
def snmp_test(profile_id):
    """Quick SNMP test against a host IP from the form."""
    from uitop.models.snmp import SnmpProfile
    from uitop.services.snmp_client import snmp_get

    user_id = session.get("user_id")
    if not user_id:
        flash("Sign in required.", "error")
        return redirect(url_for("auth.login"))
    profile = SnmpProfile.query.get(profile_id)
    if profile is None:
        flash("Profile not found.", "error")
        return redirect(url_for("network.snmp"))
    host = (request.form.get("host") or "").strip()
    if not host:
        flash("Enter a host IP to test.", "error")
        return redirect(url_for("network.snmp"))
    try:
        data = snmp_get(host, profile.community, [".1.3.6.1.2.1.1.1.0", ".1.3.6.1.2.1.1.5.0"], timeout=2.5)
        descr = data.get(".1.3.6.1.2.1.1.1.0") or data.get("1.3.6.1.2.1.1.1.0") or "OK"
        flash(f"SNMP OK on {host}: {str(descr)[:120]}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"SNMP test failed on {host}: {exc}", "error")
    return redirect(url_for("network.snmp"))


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
