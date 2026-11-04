"""Real printer SNMP polling and remote actions."""
from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Any

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.inventory import Printer
from uitop.models.snmp import SnmpProfile
from uitop.services.audit import log_audit
from uitop.services.snmp_client import snmp_get, snmp_set_integer, snmp_walk

# Standard MIBs
OID_SYS_DESCR = ".1.3.6.1.2.1.1.1.0"
OID_SYS_NAME = ".1.3.6.1.2.1.1.5.0"
OID_SYS_UPTIME = ".1.3.6.1.2.1.1.3.0"
OID_HR_PRINTER_STATUS = ".1.3.6.1.2.1.25.3.5.1.1.1"  # hrPrinterStatus.1
OID_HR_PRINTER_DETECTED = ".1.3.6.1.2.1.25.3.5.1.2.1"  # hrPrinterDetectedErrorState.1
OID_PRT_GENERAL_RESET = ".1.3.6.1.2.1.43.5.1.1.3.1"  # prtGeneralReset.1
OID_SUPPLIES_LEVEL = ".1.3.6.1.2.1.43.11.1.1.9"  # prtMarkerSuppliesLevel
OID_SUPPLIES_MAX = ".1.3.6.1.2.1.43.11.1.1.8"  # prtMarkerSuppliesMaxCapacity
OID_SUPPLIES_DESC = ".1.3.6.1.2.1.43.11.1.1.6"  # prtMarkerSuppliesDescription
OID_INPUT_LEVEL = ".1.3.6.1.2.1.43.8.2.1.10"  # prtInputCurrentLevel
OID_INPUT_MAX = ".1.3.6.1.2.1.43.8.2.1.9"  # prtInputMaxCapacity

# hrPrinterStatus values
_HR_STATUS = {
    1: "other",
    2: "unknown",
    3: "idle",
    4: "printing",
    5: "warmup",
}

ALLOWED_ACTIONS = frozenset(
    {
        "refresh_status",
        "restart",
        "print_test_page",
        "run_diagnostics",
        "open_web",
        "clear_queue",
    }
)


def utcnow():
    return datetime.now(timezone.utc)


def list_profiles() -> list[SnmpProfile]:
    return SnmpProfile.query.order_by(SnmpProfile.name).all()


def ensure_default_profile() -> SnmpProfile:
    existing = SnmpProfile.query.filter_by(name="Default public").first()
    if existing:
        return existing
    row = SnmpProfile(
        name="Default public",
        version="v2c",
        community="public",
        scope="LAN printers",
        is_write=False,
        is_active=True,
    )
    db.session.add(row)
    db.session.commit()
    return row


def create_profile(
    *,
    name: str,
    community: str,
    version: str = "v2c",
    scope: str | None = None,
    is_write: bool = False,
) -> SnmpProfile:
    name = (name or "").strip()
    community = (community or "").strip()
    if not name or not community:
        raise ValidationError("Name and community are required")
    if SnmpProfile.query.filter_by(name=name).first():
        raise ValidationError("A profile with that name already exists")
    row = SnmpProfile(
        name=name,
        version=(version or "v2c").strip(),
        community=community,
        scope=(scope or "").strip() or None,
        is_write=bool(is_write),
        is_active=True,
    )
    db.session.add(row)
    db.session.commit()
    return row


def delete_profile(profile_id: int) -> None:
    row = SnmpProfile.query.get(profile_id)
    if row is None:
        raise NotFoundError("SNMP profile not found")
    Printer.query.filter_by(snmp_profile_id=profile_id).update({"snmp_profile_id": None})
    db.session.delete(row)
    db.session.commit()


def _community_for_printer(printer: Printer) -> tuple[str, SnmpProfile | None]:
    if printer.snmp_profile_id and printer.snmp_profile:
        return printer.snmp_profile.community, printer.snmp_profile
    # try active profiles in order
    for profile in SnmpProfile.query.filter_by(is_active=True).order_by(SnmpProfile.id).all():
        return profile.community, profile
    ensure_default_profile()
    profile = SnmpProfile.query.filter_by(is_active=True).first()
    return (profile.community if profile else "public"), profile


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pct(level: Any, maximum: Any) -> int | None:
    try:
        lvl = int(level)
        mx = int(maximum)
    except (TypeError, ValueError):
        return None
    if lvl < 0:
        # -1 / -2 / -3 often mean "other / unknown / remaining unknown"
        return None
    if mx <= 0:
        # some printers report absolute remaining pages without max
        return min(100, max(0, lvl)) if lvl <= 100 else None
    return max(0, min(100, int(round(100.0 * lvl / mx))))


def poll_printer(printer: Printer, *, community: str | None = None) -> dict[str, Any]:
    ip = (printer.ip_address or "").strip()
    if not ip:
        raise ValidationError("Printer has no IP address")

    if community is None:
        community, profile = _community_for_printer(printer)
        if profile and not printer.snmp_profile_id:
            printer.snmp_profile_id = profile.id
    else:
        profile = None

    payload: dict[str, Any] = {
        "ip": ip,
        "community_used": community[:2] + "•••",
        "ports": {
            "9100": _tcp_open(ip, 9100),
            "631": _tcp_open(ip, 631),
            "80": _tcp_open(ip, 80),
            "443": _tcp_open(ip, 443),
        },
    }

    snmp_ok = False
    try:
        basic = snmp_get(
            ip,
            community,
            [OID_SYS_DESCR, OID_SYS_NAME, OID_SYS_UPTIME],
            timeout=2.5,
        )
        snmp_ok = True
        payload["sysDescr"] = basic.get(OID_SYS_DESCR) or basic.get(OID_SYS_DESCR.lstrip("."))
        payload["sysName"] = basic.get(OID_SYS_NAME) or basic.get(OID_SYS_NAME.lstrip("."))
        payload["sysUpTime"] = basic.get(OID_SYS_UPTIME) or basic.get(OID_SYS_UPTIME.lstrip("."))
    except Exception as exc:  # noqa: BLE001
        payload["snmp_error"] = str(exc)

    toner = None
    paper = None
    status = "offline"

    if snmp_ok:
        status = "online"
        try:
            st = snmp_get(ip, community, [OID_HR_PRINTER_STATUS], timeout=2.0)
            code = st.get(OID_HR_PRINTER_STATUS) or st.get(OID_HR_PRINTER_STATUS.lstrip("."))
            payload["hrPrinterStatus"] = code
            label = _HR_STATUS.get(int(code), "online") if code is not None else "online"
            if label == "printing":
                status = "online"
            elif label in {"warmup", "idle"}:
                status = "online"
            elif label == "unknown":
                status = "warning"
        except Exception as exc:  # noqa: BLE001
            payload["status_error"] = str(exc)

        try:
            levels = snmp_walk(ip, community, OID_SUPPLIES_LEVEL, max_items=20)
            maxes = dict(snmp_walk(ip, community, OID_SUPPLIES_MAX, max_items=20))
            descs = dict(snmp_walk(ip, community, OID_SUPPLIES_DESC, max_items=20))
            supplies = []
            toner_candidates = []
            for oid, level in levels:
                suffix = oid[len(OID_SUPPLIES_LEVEL) :]
                mx = maxes.get(OID_SUPPLIES_MAX + suffix)
                desc = descs.get(OID_SUPPLIES_DESC + suffix) or ""
                pct = _pct(level, mx)
                supplies.append({"oid": oid, "level": level, "max": mx, "percent": pct, "description": desc})
                desc_l = str(desc).lower()
                if pct is not None and any(k in desc_l for k in ("toner", "ink", "cartridge", "black", "cyan", "magenta", "yellow")):
                    toner_candidates.append(pct)
                elif pct is not None and not desc:
                    toner_candidates.append(pct)
            payload["supplies"] = supplies
            if toner_candidates:
                toner = min(toner_candidates)
        except Exception as exc:  # noqa: BLE001
            payload["supplies_error"] = str(exc)

        try:
            in_levels = snmp_walk(ip, community, OID_INPUT_LEVEL, max_items=12)
            in_maxes = dict(snmp_walk(ip, community, OID_INPUT_MAX, max_items=12))
            trays = []
            paper_candidates = []
            for oid, level in in_levels:
                suffix = oid[len(OID_INPUT_LEVEL) :]
                mx = in_maxes.get(OID_INPUT_MAX + suffix)
                pct = _pct(level, mx)
                trays.append({"oid": oid, "level": level, "max": mx, "percent": pct})
                if pct is not None:
                    paper_candidates.append(pct)
            payload["trays"] = trays
            if paper_candidates:
                paper = min(paper_candidates)
        except Exception as exc:  # noqa: BLE001
            payload["trays_error"] = str(exc)

        if toner is not None and toner <= 15:
            status = "low toner"
        if paper is not None and paper == 0:
            status = "out of paper"

    elif payload["ports"].get("9100") or payload["ports"].get("631"):
        status = "online"
        payload["note"] = "Reachable on print ports but SNMP failed (wrong community or SNMP disabled)"

    # Persist
    printer.status = status
    printer.last_seen_at = utcnow()
    printer.last_snmp_at = utcnow() if snmp_ok else printer.last_snmp_at
    printer.toner_percent = toner
    printer.paper_percent = paper
    if printer.queue_depth is None:
        printer.queue_depth = 0
    sys_descr = payload.get("sysDescr")
    if isinstance(sys_descr, str) and sys_descr:
        printer.snmp_sys_descr = sys_descr[:512]
        if not printer.model or printer.model in {"Unknown", "—"}:
            printer.model = sys_descr[:120]
    sys_name = payload.get("sysName")
    if isinstance(sys_name, str) and sys_name and (not printer.name or printer.name.startswith("host-")):
        printer.name = sys_name[:255]
    printer.snmp_payload = payload
    db.session.commit()

    return {
        "printer_id": printer.id,
        "status": status,
        "toner_percent": toner,
        "paper_percent": paper,
        "queue_depth": printer.queue_depth or 0,
        "snmp_ok": snmp_ok,
        "payload": payload,
    }


def restart_printer(printer: Printer) -> str:
    ip = (printer.ip_address or "").strip()
    if not ip:
        raise ValidationError("Printer has no IP address")
    community, profile = _community_for_printer(printer)
    # Prefer write community if available
    write_profile = SnmpProfile.query.filter_by(is_active=True, is_write=True).first()
    if write_profile:
        community = write_profile.community
        profile = write_profile
    try:
        # Printer-MIB prtGeneralReset: powerCycleReset(4)
        snmp_set_integer(ip, community, OID_PRT_GENERAL_RESET, 4, timeout=3.0)
        msg = "SNMP power-cycle reset sent (prtGeneralReset=4)"
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(
            f"SNMP restart failed ({exc}). Use a write community, or reboot from the printer web UI."
        ) from exc
    log_audit(
        "printers.restart",
        resource_type="printer",
        resource_id=printer.id,
        meta={"ip": ip, "profile": profile.name if profile else None},
    )
    return msg


def print_test_page(printer: Printer) -> str:
    """Send a simple text test page to JetDirect (TCP 9100)."""
    ip = (printer.ip_address or "").strip()
    if not ip:
        raise ValidationError("Printer has no IP address")
    body = (
        "\x1b%-12345X@PJL JOB NAME=\"UITOP-TEST\"\r\n"
        "@PJL ENTER LANGUAGE=PCL\r\n"
        "\x1bE"
        "UITOP Printer Test Page\r\n"
        f"Printer: {printer.name}\r\n"
        f"IP: {ip}\r\n"
        f"Time: {utcnow().isoformat()}\r\n"
        "If you can read this, JetDirect (9100) is working.\r\n"
        "\x0c"
        "\x1b%-12345X@PJL EOJ\r\n"
        "\x1b%-12345X"
    ).encode("latin-1", errors="replace")
    try:
        with socket.create_connection((ip, 9100), timeout=5) as sock:
            sock.sendall(body)
    except OSError as exc:
        # Fallback: plain text
        try:
            text = (
                f"UITOP Test Page\nPrinter: {printer.name}\nIP: {ip}\n"
                f"Time: {utcnow().isoformat()}\n\n\x0c"
            ).encode("utf-8", errors="replace")
            with socket.create_connection((ip, 9100), timeout=5) as sock:
                sock.sendall(text)
        except OSError as exc2:
            raise ValidationError(f"Cannot reach printer on port 9100: {exc2}") from exc
    log_audit("printers.test_page", resource_type="printer", resource_id=printer.id, meta={"ip": ip})
    return "Test page sent to TCP 9100 (JetDirect)"


def clear_queue(printer: Printer) -> str:
    """Best-effort: printers rarely expose queue clear via SNMP; reset to NVRAM if write allowed."""
    ip = (printer.ip_address or "").strip()
    if not ip:
        raise ValidationError("Printer has no IP address")
    write_profile = SnmpProfile.query.filter_by(is_active=True, is_write=True).first()
    if not write_profile:
        raise ValidationError(
            "Clear queue via SNMP needs a write community. Add one under Network → SNMP, "
            "or clear jobs on the Windows print server."
        )
    try:
        # resetToNVRAM(5) — clears volatile state on many devices
        snmp_set_integer(ip, write_profile.community, OID_PRT_GENERAL_RESET, 5, timeout=3.0)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"SNMP clear/reset failed: {exc}") from exc
    printer.queue_depth = 0
    db.session.commit()
    log_audit("printers.clear_queue", resource_type="printer", resource_id=printer.id, meta={"ip": ip})
    return "SNMP resetToNVRAM sent (queue clear best-effort)"


def run_diagnostics(printer: Printer) -> dict[str, Any]:
    result = poll_printer(printer)
    ports = (result.get("payload") or {}).get("ports") or {}
    checks = [
        f"SNMP: {'OK' if result.get('snmp_ok') else 'FAIL'}",
        f"JetDirect 9100: {'open' if ports.get('9100') else 'closed'}",
        f"IPP 631: {'open' if ports.get('631') else 'closed'}",
        f"HTTP 80: {'open' if ports.get('80') else 'closed'}",
        f"Status: {result.get('status')}",
        f"Toner: {result.get('toner_percent') if result.get('toner_percent') is not None else 'n/a'}%",
        f"Paper: {result.get('paper_percent') if result.get('paper_percent') is not None else 'n/a'}%",
    ]
    result["diagnostics"] = checks
    result["message"] = " · ".join(checks)
    log_audit("printers.diagnostics", resource_type="printer", resource_id=printer.id, meta={"checks": checks})
    return result


def run_action(printer_id: int, action: str, *, actor_user_id: int | None = None) -> dict[str, Any]:
    printer = Printer.query.get(printer_id)
    if printer is None:
        raise NotFoundError("Printer not found")
    act = (action or "").strip().lower()
    if act not in ALLOWED_ACTIONS:
        raise ValidationError(f"Unsupported action: {action}")

    if act == "refresh_status":
        data = poll_printer(printer)
        return {"ok": True, "message": f"Status refreshed · {data['status']}", "data": data}
    if act == "restart":
        msg = restart_printer(printer)
        return {"ok": True, "message": msg}
    if act == "print_test_page":
        msg = print_test_page(printer)
        return {"ok": True, "message": msg}
    if act == "clear_queue":
        msg = clear_queue(printer)
        return {"ok": True, "message": msg}
    if act == "run_diagnostics":
        data = run_diagnostics(printer)
        return {"ok": True, "message": data["message"], "data": data}
    if act == "open_web":
        ip = printer.ip_address or ""
        return {"ok": True, "message": f"Open http://{ip}", "url": f"http://{ip}"}
    raise ValidationError(f"Unsupported action: {action}")
