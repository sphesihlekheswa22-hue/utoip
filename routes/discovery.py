"""LAN discovery API used by Computers / Network / Servers / Printers scan UIs."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session

from uitop.core.permissions import (
    COMPUTERS_READ,
    COMPUTERS_WRITE,
    NETWORK_READ,
    NETWORK_WRITE,
    PRINTERS_READ,
    PRINTERS_WRITE,
    SERVERS_READ,
    SERVERS_WRITE,
)
from uitop.core.ui_rbac import has_perm
from uitop.services import network_scan as scan_svc

bp = Blueprint("discovery", __name__, url_prefix="/discovery")

_READ_ANY = (COMPUTERS_READ, NETWORK_READ, SERVERS_READ, PRINTERS_READ)
_WRITE_ANY = (COMPUTERS_WRITE, NETWORK_WRITE, SERVERS_WRITE, PRINTERS_WRITE)


def _require_read():
    if not session.get("user_id") or not has_perm(*_READ_ANY):
        return jsonify({"error": "Forbidden"}), 403
    return None


def _require_write():
    if not session.get("user_id") or not has_perm(*_WRITE_ANY):
        return jsonify({"error": "Forbidden"}), 403
    return None


@bp.get("/suggest")
def suggest():
    denied = _require_read()
    if denied:
        return denied
    return jsonify({"cidrs": scan_svc.detect_local_cidrs()})


@bp.post("/scan")
def start_scan():
    denied = _require_read()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    cidr = (payload.get("cidr") or request.form.get("cidr") or "").strip()
    filter_type = (payload.get("filter") or request.form.get("filter") or "").strip() or None
    if not cidr:
        suggested = scan_svc.detect_local_cidrs()
        cidr = suggested[0] if suggested else ""
    try:
        job_id = scan_svc.start_scan_job_with_app(
            current_app._get_current_object(),  # type: ignore[attr-defined]
            cidr,
            filter_type=filter_type,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"job_id": job_id, "cidr": cidr, "filter": filter_type})


@bp.get("/scan/<job_id>")
def scan_status(job_id: str):
    denied = _require_read()
    if denied:
        return denied
    job = scan_svc.get_job(job_id)
    if not job:
        return jsonify({"error": "Scan job not found"}), 404
    return jsonify(job)


@bp.post("/import")
def import_hosts():
    denied = _require_write()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    hosts = payload.get("hosts") or []
    prefer_type = (payload.get("prefer_type") or "").strip() or None
    if not isinstance(hosts, list) or not hosts:
        return jsonify({"error": "No hosts provided"}), 400
    result = scan_svc.import_hosts(hosts, prefer_type=prefer_type)
    return jsonify(result)
