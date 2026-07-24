"""Map Computer / telemetry models into UI-friendly dicts for Jinja + Alpine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uitop.models.agent_telemetry import AgentAlert, AgentEvent, PerformanceSample
from uitop.models.department import Department
from uitop.models.inventory import Computer


def utcnow():
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def relative_time(dt: datetime | None) -> str:
    if dt is None:
        return "Never"
    dt = _as_utc(dt)
    now = utcnow()
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "Just now"
    if seconds < 45:
        return "Just now"
    if seconds < 3600:
        mins = max(1, seconds // 60)
        return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
    days = seconds // 86400
    return f"{days} day ago" if days == 1 else f"{days} days ago"


def derive_presence(computer: Computer, *, offline_after: timedelta = timedelta(minutes=15)) -> tuple[str, str]:
    """Return (status_label, agent_label) for UI badges."""
    last = _as_utc(computer.last_seen_at)
    raw = (computer.status or "unknown").strip().lower()
    has_agent = bool(computer.agent_id)

    if not has_agent:
        return "Offline", "Missing"

    if last is None:
        return "Offline", "Offline"

    stale = utcnow() - last > offline_after
    if stale:
        return "Offline", "Offline"

    if raw in {"critical", "warning", "online", "registered"}:
        label = raw.title() if raw != "registered" else "Online"
        if raw == "registered":
            label = "Online"
        elif raw == "critical":
            label = "Critical"
        elif raw == "warning":
            label = "Warning"
        else:
            label = "Online"
        return label, "Online"

    return "Online", "Online"


def _os_family(os_name: str | None, os_version: str | None = None) -> str:
    text = f"{os_name or ''} {os_version or ''}".lower()
    if "windows 11" in text or "win 11" in text:
        return "Windows 11"
    if "windows 10" in text or "win 10" in text:
        return "Windows 10"
    if "windows server" in text:
        return "Windows Server"
    if os_name:
        return os_name.split()[0:2] and " ".join(os_name.split()[:2]) or os_name
    return "Unknown"


def _guess_type(hostname: str | None, model: str | None) -> str:
    blob = f"{hostname or ''} {model or ''}".lower()
    if any(x in blob for x in ("lap", "notebook", "elitebook", "latitude", "xps", "macbook")):
        return "Laptop"
    if "kiosk" in blob:
        return "Kiosk"
    if any(x in blob for x in ("workstation", "thinkstation", "precision", "cad")):
        return "Workstation"
    return "Desktop"


def _criticality(status: str) -> str:
    if status == "Critical":
        return "Critical"
    if status == "Warning":
        return "High"
    if status == "Offline":
        return "Medium"
    return "Low"


def latest_sample(computer_id: int) -> PerformanceSample | None:
    return (
        PerformanceSample.query.filter_by(computer_id=computer_id)
        .order_by(PerformanceSample.collected_at.desc())
        .first()
    )


def serialize_computer(computer: Computer, sample: PerformanceSample | None = None) -> dict:
    status, agent = derive_presence(computer)
    dept_name = computer.department.name if getattr(computer, "department", None) else "—"
    os_display = " ".join(x for x in [computer.os_name, computer.os_version] if x) or "Unknown"

    if sample is None:
        sample = latest_sample(computer.id)

    cpu = int(round(sample.cpu_percent)) if sample and sample.cpu_percent is not None else 0
    ram = int(round(sample.memory_percent)) if sample and sample.memory_percent is not None else 0
    disk = int(round(sample.disk_percent)) if sample and sample.disk_percent is not None else 0

    return {
        "id": computer.id,
        "name": computer.hostname,
        "hostname": computer.hostname,
        "user": "—",
        "department": dept_name,
        "department_id": computer.department_id,
        "os": os_display,
        "os_family": _os_family(computer.os_name, computer.os_version),
        "os_name": computer.os_name,
        "os_version": computer.os_version,
        "ip": computer.ip_address or "—",
        "mac": computer.mac_address or "—",
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "last_seen": relative_time(computer.last_seen_at),
        "last_seen_at": computer.last_seen_at.isoformat() if computer.last_seen_at else None,
        "status": status,
        "agent": agent,
        "agent_id": computer.agent_id,
        "agent_version": computer.agent_version or "—",
        "type": _guess_type(computer.hostname, computer.model),
        "manufacturer": computer.manufacturer or "—",
        "model": computer.model or "—",
        "serial_number": computer.serial_number or "—",
        "asset_tag": computer.asset_tag or "—",
        "domain": computer.domain or "—",
        "cpu_model": computer.cpu_model or "—",
        "cpu_cores": computer.cpu_cores,
        "ram_gb": computer.ram_gb,
        "disk_gb": computer.disk_gb,
        "criticality": _criticality(status),
        "inventory_updated_at": relative_time(computer.inventory_updated_at)
        if computer.inventory_updated_at
        else "Never",
    }


def list_computers_for_ui() -> list[dict]:
    rows = Computer.query.order_by(Computer.hostname.asc()).all()
    # Prefetch latest samples in one pass where possible
    result = []
    for row in rows:
        result.append(serialize_computer(row))
    return result


def computer_kpis(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "online": sum(1 for r in rows if r["status"] == "Online"),
        "offline": sum(1 for r in rows if r["status"] == "Offline"),
        "critical": sum(1 for r in rows if r["status"] == "Critical"),
        "warning": sum(1 for r in rows if r["status"] == "Warning"),
        "agent_installed": sum(1 for r in rows if r.get("agent_id")),
        "agent_offline": sum(1 for r in rows if r["agent"] == "Offline"),
        "pending_updates": sum(1 for r in rows if r["status"] in {"Warning", "Critical"}),
    }


def get_computer_or_none(item_id: int) -> Computer | None:
    return Computer.query.get(item_id)


def performance_series(computer_id: int, limit: int = 30) -> list[dict]:
    samples = (
        PerformanceSample.query.filter_by(computer_id=computer_id)
        .order_by(PerformanceSample.collected_at.desc())
        .limit(limit)
        .all()
    )
    samples.reverse()
    return [
        {
            "t": s.collected_at.isoformat() if s.collected_at else None,
            "cpu": s.cpu_percent,
            "mem": s.memory_percent,
            "disk": s.disk_percent,
            "net_sent": s.network_bytes_sent,
            "net_recv": s.network_bytes_recv,
        }
        for s in samples
    ]


def recent_events(computer_id: int, limit: int = 20) -> list[dict]:
    rows = (
        AgentEvent.query.filter_by(computer_id=computer_id)
        .order_by(AgentEvent.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return [r.to_dict() for r in rows]


def recent_alerts(computer_id: int, limit: int = 20) -> list[dict]:
    rows = (
        AgentAlert.query.filter_by(computer_id=computer_id)
        .order_by(AgentAlert.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return [r.to_dict() for r in rows]


def department_names() -> list[str]:
    return [d.name for d in Department.query.order_by(Department.name).all()]
