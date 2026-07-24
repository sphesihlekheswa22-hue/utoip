"""UI serializers for servers, network devices, and printers (live DB)."""
from __future__ import annotations

from datetime import timedelta

from types import SimpleNamespace

from uitop.models.inventory import NetworkDevice, Printer, Server
from uitop.services.computers_view import derive_presence, relative_time, utcnow, _as_utc


def _status_label(raw: str | None, last_seen_at, *, offline_after=timedelta(minutes=30)) -> str:
    """Presence for non-agent-heavy assets (network / printers)."""
    last = _as_utc(last_seen_at)
    status = (raw or "unknown").strip().lower()

    if last is not None and utcnow() - last > offline_after:
        return "Offline"

    mapping = {
        "online": "Online",
        "offline": "Offline",
        "warning": "Warning",
        "critical": "Critical",
        "unknown": "Offline",
        "low toner": "Low Toner",
        "out of paper": "Out of Paper",
        "paper jam": "Paper Jam",
        "needs maintenance": "Needs Maintenance",
    }
    return mapping.get(status, status.title() if status else "Offline")


def serialize_server(server: Server) -> dict:
    proxy = SimpleNamespace(
        status=server.status,
        agent_id=server.agent_id,
        last_seen_at=server.last_seen_at,
    )
    status, agent = derive_presence(proxy)  # type: ignore[arg-type]
    os_name = server.os_name or "Unknown"
    os_family = "Windows" if "windows" in os_name.lower() else ("Linux" if "linux" in os_name.lower() else "Other")
    dept = server.department.name if getattr(server, "department", None) else "—"

    return {
        "id": server.id,
        "name": server.hostname,
        "hostname": server.hostname,
        "ip": server.ip_address or "—",
        "os": os_name,
        "os_family": os_family,
        "role": server.role or "—",
        "cpu": 0,
        "ram": 0,
        "disk": 0,
        "uptime": "—",
        "last_seen": relative_time(server.last_seen_at),
        "status": status,
        "agent": agent,
        "agent_id": server.agent_id,
        "agent_version": server.agent_version or "—",
        "virt": "Physical",
        "department": dept,
        "location": "—",
        "criticality": "Critical" if status == "Critical" else ("High" if status == "Warning" else "Medium"),
        "asset_tag": server.asset_tag or "—",
    }


def list_servers_for_ui() -> list[dict]:
    return [serialize_server(s) for s in Server.query.order_by(Server.hostname).all()]


def server_kpis(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "online": sum(1 for r in rows if r["status"] == "Online"),
        "offline": sum(1 for r in rows if r["status"] == "Offline"),
        "critical": sum(1 for r in rows if r["status"] == "Critical"),
        "high_cpu": sum(1 for r in rows if r.get("cpu", 0) >= 70),
        "high_mem": sum(1 for r in rows if r.get("ram", 0) >= 80),
        "high_disk": sum(1 for r in rows if r.get("disk", 0) >= 80),
        "agent_installed": sum(1 for r in rows if r.get("agent_id")),
        "pending_updates": sum(1 for r in rows if r["status"] in {"Warning", "Critical"}),
    }


def serialize_network_device(dev: NetworkDevice) -> dict:
    status = _status_label(dev.status, dev.last_seen_at)
    dtype = (dev.device_type or "device").replace("_", " ").title()
    if dtype.lower() == "access point":
        dtype = "Access Point"
    bandwidth = 55 if status == "Online" else (75 if status == "Warning" else 0)
    return {
        "id": dev.id,
        "name": dev.hostname,
        "hostname": dev.hostname,
        "ip": dev.ip_address or "—",
        "mac": dev.mac_address or "—",
        "type": dtype,
        "manufacturer": dev.vendor or "—",
        "model": dtype,
        "firmware": "—",
        "status": status,
        "bandwidth": bandwidth,
        "uptime": "—",
        "last_seen": relative_time(dev.last_seen_at),
        "location": "—",
        "criticality": "Critical" if status in {"Critical", "Offline"} else ("High" if status == "Warning" else "Medium"),
        "agent_id": dev.agent_id,
        "agent_version": dev.agent_version or "—",
    }


def list_network_for_ui() -> list[dict]:
    return [serialize_network_device(d) for d in NetworkDevice.query.order_by(NetworkDevice.hostname).all()]


def network_kpis(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "online": sum(1 for r in rows if r["status"] == "Online"),
        "offline": sum(1 for r in rows if r["status"] == "Offline"),
        "critical": sum(1 for r in rows if r["status"] == "Critical"),
        "warnings": sum(1 for r in rows if r["status"] == "Warning"),
        "bandwidth": f"{sum(r.get('bandwidth', 0) for r in rows) // max(len(rows), 1)}%",
        "high_traffic": sum(1 for r in rows if r.get("bandwidth", 0) >= 70),
        "health": "Good" if not any(r["status"] in ("Critical", "Offline") for r in rows) else "Degraded",
    }


def serialize_printer(printer: Printer) -> dict:
    status = _status_label(printer.status, printer.last_seen_at)
    # Map DB statuses into printer-centric labels when needed
    raw = (printer.status or "").lower()
    if "toner" in raw:
        status = "Low Toner"
    elif "paper" in raw and "jam" in raw:
        status = "Paper Jam"
    elif "paper" in raw:
        status = "Out of Paper"
    elif "maintenance" in raw:
        status = "Needs Maintenance"

    dept = printer.department.name if getattr(printer, "department", None) else "—"
    model = printer.model or "—"
    manufacturer = model.split()[0] if model and model != "—" else "—"

    toner = 62
    paper = 70
    queue = 0
    if status == "Low Toner":
        toner = 12
    elif status == "Out of Paper":
        paper = 0
        queue = 3
    elif status == "Paper Jam":
        paper = 20
        queue = 2
    elif status == "Offline":
        toner = 0
        paper = 0
    elif status == "Warning":
        toner = 25

    return {
        "id": printer.id,
        "name": printer.name,
        "model": model,
        "ip": printer.ip_address or "—",
        "location": printer.location or "—",
        "department": dept,
        "status": status,
        "toner": toner,
        "paper": paper,
        "queue": queue,
        "last_seen": relative_time(printer.last_seen_at),
        "manufacturer": manufacturer,
        "type": "MFP" if "mfp" in model.lower() else "Network Printer",
        "color": True,
        "network": True,
        "agent_id": printer.agent_id,
        "agent_version": printer.agent_version or "—",
    }


def list_printers_for_ui() -> list[dict]:
    return [serialize_printer(p) for p in Printer.query.order_by(Printer.name).all()]


def printer_kpis(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "online": sum(1 for r in rows if r["status"] == "Online"),
        "offline": sum(1 for r in rows if r["status"] == "Offline"),
        "out_of_paper": sum(1 for r in rows if r["status"] == "Out of Paper" or r.get("paper") == 0),
        "low_toner": sum(1 for r in rows if r.get("toner", 100) <= 15 or r["status"] == "Low Toner"),
        "paper_jam": sum(1 for r in rows if r["status"] == "Paper Jam"),
        "critical": sum(1 for r in rows if r["status"] == "Critical"),
        "maintenance": sum(1 for r in rows if r["status"] == "Needs Maintenance"),
    }
