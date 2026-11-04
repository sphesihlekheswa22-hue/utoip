"""Real LAN discovery — ICMP + TCP port fingerprinting."""
from __future__ import annotations

import ipaddress
import platform
import socket
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from uitop.extensions import db
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server

# Safety: only RFC1918, and never wider than /24 in one job.
_PRIVATE = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

_PROBE_PORTS = (
    22,  # SSH
    80,  # HTTP
    139,  # NetBIOS
    443,  # HTTPS
    445,  # SMB
    515,  # LPD
    631,  # IPP
    3389,  # RDP
    5985,  # WinRM
    9100,  # JetDirect
)

_MAX_HOSTS = 256
_WORKERS = 64
_TCP_TIMEOUT = 0.35
_PING_TIMEOUT_MS = 400

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


@dataclass
class HostResult:
    ip: str
    hostname: str = ""
    type: str = "Unknown"
    os: str = "Unknown"
    vendor: str = "—"
    ports: list[int] = field(default_factory=list)
    status: str = "Online"
    alive_via: str = ""
    managed: bool = False
    inventory_id: int | None = None
    inventory_kind: str | None = None
    agent: str = "Agent Missing"
    snmp: bool = False
    source: str = "Network"
    model: str = "Unknown"
    name: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d.get("name"):
            d["name"] = d["hostname"] or d["ip"]
        return d


def detect_local_cidrs() -> list[str]:
    """Suggest /24 CIDRs for local IPv4 interfaces (best-effort)."""
    found: set[str] = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            if _is_private_network(net):
                found.add(str(net))
    except OSError:
        pass

    # Default-route interface IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            if _is_private_network(net):
                found.add(str(net))
    except OSError:
        pass

    return sorted(found) or ["192.168.1.0/24"]


def _is_private_network(net: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
    if not isinstance(net, ipaddress.IPv4Network):
        return False
    return any(net.subnet_of(p) for p in _PRIVATE)


def validate_cidr(cidr: str) -> ipaddress.IPv4Network:
    raw = (cidr or "").strip()
    if not raw:
        raise ValueError("Subnet CIDR is required (e.g. 192.168.1.0/24).")
    try:
        net = ipaddress.ip_network(raw, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR: {raw}") from exc
    if not isinstance(net, ipaddress.IPv4Network):
        raise ValueError("Only IPv4 subnets are supported.")
    if net.num_addresses - 2 > _MAX_HOSTS:
        raise ValueError(f"Subnet too large (max /24, {_MAX_HOSTS} hosts). Use a smaller CIDR.")
    if not _is_private_network(net):
        raise ValueError("Only private (RFC1918) subnets can be scanned.")
    return net


def get_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def start_scan_job_with_app(app, cidr: str, *, filter_type: str | None = None) -> str:
    """Start scan with explicit Flask app for DB enrichment in worker thread."""
    net = validate_cidr(cidr)
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "progress": 0,
            "status_text": f"Scanning {net}…",
            "cidr": str(net),
            "filter_type": filter_type,
            "hosts": [],
            "totals": {},
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }
    t = threading.Thread(
        target=_run_job_with_app,
        args=(app, job_id, str(net), filter_type),
        daemon=True,
    )
    t.start()
    return job_id


def _run_job_with_app(app, job_id: str, cidr: str, filter_type: str | None) -> None:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        assert isinstance(net, ipaddress.IPv4Network)
        hosts = list(net.hosts())
        total = len(hosts) or 1
        results: list[HostResult] = []
        done = 0

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            futures = {pool.submit(_probe_host, str(ip)): str(ip) for ip in hosts}
            for fut in as_completed(futures):
                done += 1
                host = fut.result()
                if host is not None:
                    results.append(host)
                progress = min(99, int(done * 100 / total))
                with _jobs_lock:
                    job = _jobs.get(job_id)
                    if job:
                        job["progress"] = progress
                        job["status_text"] = f"Probed {done}/{total} hosts · {len(results)} alive"

        with app.app_context():
            for h in results:
                _enrich_host(h)
            totals = _compute_totals(results)
            if filter_type:
                results = [h for h in results if _matches_filter(h, filter_type)]
            totals["discovered"] = len(results)

        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["hosts"] = [h.to_dict() for h in sorted(results, key=lambda x: ipaddress.ip_address(x.ip))]
                job["totals"] = totals
                job["progress"] = 100
                job["status"] = "done"
                job["status_text"] = f"Scan complete — {len(results)} host(s) found on {cidr}."
                job["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:  # noqa: BLE001
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "error"
                job["error"] = str(exc)
                job["status_text"] = f"Scan failed: {exc}"
                job["progress"] = 100
                job["finished_at"] = datetime.now(timezone.utc).isoformat()


def _probe_host(ip: str) -> HostResult | None:
    ping_ok = _ping(ip)
    open_ports = _scan_ports(ip)
    if not ping_ok and not open_ports:
        return None
    host = HostResult(
        ip=ip,
        ports=open_ports,
        alive_via="icmp+tcp" if ping_ok and open_ports else ("icmp" if ping_ok else "tcp"),
        status="Online",
    )
    host.type = _classify(open_ports)
    host.os = _guess_os(open_ports, host.type)
    host.hostname = ip
    host.name = ip
    return host


def _ping(ip: str) -> bool:
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(_PING_TIMEOUT_MS), ip]
    else:
        # Linux/mac: -c 1, -W seconds
        timeout_s = max(1, int(_PING_TIMEOUT_MS / 1000) or 1)
        cmd = ["ping", "-c", "1", "-W", str(timeout_s), ip]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _scan_ports(ip: str) -> list[int]:
    open_ports: list[int] = []
    for port in _PROBE_PORTS:
        try:
            with socket.create_connection((ip, port), timeout=_TCP_TIMEOUT):
                open_ports.append(port)
        except OSError:
            continue
    return open_ports


def _classify(ports: list[int]) -> str:
    ps = set(ports)
    if ps & {9100, 515, 631}:
        return "Printer"
    windows = bool(ps & {445, 139, 3389, 5985})
    if windows:
        # Heuristic: WinRM/RDP without workstation SMB-only still computer;
        # treat as Server when SSH also open (mixed) or only server-ish.
        if 22 in ps and 445 not in ps:
            return "Server"
        return "Computer"
    if 22 in ps:
        return "Server"
    if ps & {80, 443} and not windows:
        # Likely network appliance / AP / firewall UI
        if 443 in ps and 80 in ps:
            return "Network"
        return "Network"
    if ports:
        return "Unknown"
    return "Unknown"


def _guess_os(ports: list[int], dtype: str) -> str:
    ps = set(ports)
    if dtype == "Printer":
        return "Printer firmware"
    if 445 in ps or 139 in ps or 3389 in ps or 5985 in ps:
        return "Windows"
    if 22 in ps:
        return "Linux / Unix"
    if dtype == "Network":
        return "Network OS"
    return "Unknown"


def _enrich_host(host: HostResult) -> None:
    try:
        name, _, _ = socket.gethostbyaddr(host.ip)
        if name:
            host.hostname = name.split(".")[0]
            host.name = host.hostname
    except OSError:
        host.hostname = f"host-{host.ip.replace('.', '-')}"
        host.name = host.hostname

    # Inventory match by IP
    computer = Computer.query.filter_by(ip_address=host.ip).first()
    if computer:
        host.managed = True
        host.inventory_id = computer.id
        host.inventory_kind = "computer"
        host.agent = "Agent Installed" if computer.agent_id else "Agent Missing"
        host.hostname = computer.hostname or host.hostname
        host.name = host.hostname
        host.os = computer.os_name or host.os
        host.type = "Computer"
        return

    server = Server.query.filter_by(ip_address=host.ip).first()
    if server:
        host.managed = True
        host.inventory_id = server.id
        host.inventory_kind = "server"
        host.agent = "Agent Installed" if server.agent_id else "Agent Missing"
        host.hostname = server.hostname or host.hostname
        host.name = host.hostname
        host.os = server.os_name or host.os
        host.type = "Server"
        return

    printer = Printer.query.filter_by(ip_address=host.ip).first()
    if printer:
        host.managed = True
        host.inventory_id = printer.id
        host.inventory_kind = "printer"
        host.agent = "Agent Installed" if printer.agent_id else "Agent Missing"
        host.hostname = printer.name or host.hostname
        host.name = host.hostname
        host.model = printer.model or host.model
        host.type = "Printer"
        return

    netdev = NetworkDevice.query.filter_by(ip_address=host.ip).first()
    if netdev:
        host.managed = True
        host.inventory_id = netdev.id
        host.inventory_kind = "network"
        host.agent = "Agent Installed" if netdev.agent_id else "Agent Missing"
        host.hostname = netdev.hostname or host.hostname
        host.name = host.hostname
        host.vendor = netdev.vendor or host.vendor
        host.type = netdev.device_type or host.type or "Network"
        host.snmp = True
        return

    host.managed = False
    host.agent = "Agent Missing"


def _matches_filter(host: HostResult, filter_type: str) -> bool:
    ft = (filter_type or "").strip().lower()
    if not ft or ft == "all":
        return True
    if ft == "computers":
        # Include unclassified live hosts so operators can import them as PCs
        return host.type in {"Computer", "Unknown"}
    if ft == "servers":
        return host.type == "Server"
    if ft == "printers":
        return host.type == "Printer"
    if ft == "network":
        return host.type in {"Network", "Router", "Switch", "Firewall", "Unknown"}
    return True


def _compute_totals(hosts: list[HostResult]) -> dict[str, int]:
    totals = {
        "devices": len(hosts),
        "computers": 0,
        "servers": 0,
        "printers": 0,
        "network": 0,
        "routers": 0,
        "switches": 0,
        "firewalls": 0,
        "unknown": 0,
        "discovered": len(hosts),
        "managed": 0,
        "unmanaged": 0,
        "offline": 0,
        "sources": 1,
    }
    for h in hosts:
        t = (h.type or "Unknown").lower()
        if t == "computer":
            totals["computers"] += 1
        elif t == "server":
            totals["servers"] += 1
        elif t == "printer":
            totals["printers"] += 1
        elif t in {"network", "router", "switch", "firewall", "access point", "nas"}:
            totals["network"] += 1
            if t == "router":
                totals["routers"] += 1
            elif t == "switch":
                totals["switches"] += 1
            elif t == "firewall":
                totals["firewalls"] += 1
        else:
            totals["unknown"] += 1
        if h.managed:
            totals["managed"] += 1
        else:
            totals["unmanaged"] += 1
        if h.status != "Online":
            totals["offline"] += 1
    return totals


def import_hosts(hosts: list[dict[str, Any]], *, prefer_type: str | None = None) -> dict[str, Any]:
    """Create inventory rows for discovered hosts that are not already managed."""
    created = []
    skipped = []
    for raw in hosts:
        ip = (raw.get("ip") or "").strip()
        if not ip:
            continue
        dtype = (prefer_type or raw.get("type") or "Unknown").strip()
        hostname = (raw.get("hostname") or raw.get("name") or f"host-{ip.replace('.', '-')}").strip()
        os_name = (raw.get("os") or None)

        existing = _find_by_ip(ip)
        if existing:
            skipped.append({"ip": ip, "reason": "already_exists", "kind": existing[0], "id": existing[1]})
            continue

        now = datetime.now(timezone.utc)
        if dtype == "Server":
            row = Server(
                hostname=hostname[:255],
                ip_address=ip,
                os_name=(os_name or "Unknown")[:120] if os_name else "Unknown",
                status="online",
                last_seen_at=now,
            )
            kind = "server"
        elif dtype == "Printer":
            row = Printer(
                name=hostname[:255],
                ip_address=ip,
                model=(raw.get("model") or "Unknown")[:120],
                status="online",
                last_seen_at=now,
            )
            kind = "printer"
        elif dtype in {"Network", "Router", "Switch", "Firewall"}:
            row = NetworkDevice(
                hostname=hostname[:255],
                ip_address=ip,
                device_type=dtype if dtype != "Network" else "Network",
                vendor=(raw.get("vendor") or None),
                status="online",
                last_seen_at=now,
            )
            kind = "network"
        else:
            # Default Computer (and Unknown → Computer for computers scan import)
            row = Computer(
                hostname=hostname[:255],
                ip_address=ip,
                os_name=(os_name or "Unknown")[:120] if os_name else "Unknown",
                status="online",
                last_seen_at=now,
            )
            kind = "computer"

        db.session.add(row)
        db.session.flush()
        created.append({"ip": ip, "kind": kind, "id": row.id, "hostname": hostname})

    db.session.commit()
    return {"created": created, "skipped": skipped, "created_count": len(created), "skipped_count": len(skipped)}


def upsert_discovered_hosts(
    hosts: list[dict[str, Any]],
    *,
    prefer_type: str | None = None,
    site_id: int | None = None,
) -> dict[str, Any]:
    """Create or refresh inventory rows from a site-connector LAN scan."""
    created: list[dict] = []
    updated: list[dict] = []
    skipped: list[dict] = []
    now = datetime.now(timezone.utc)

    for raw in hosts:
        ip = (raw.get("ip") or "").strip()
        if not ip:
            continue
        dtype = (prefer_type or raw.get("type") or "Unknown").strip()
        hostname = (raw.get("hostname") or raw.get("name") or f"host-{ip.replace('.', '-')}").strip()
        os_name = raw.get("os") or None
        existing = _find_by_ip(ip)

        if existing:
            kind, row_id = existing
            row = _get_inventory_row(kind, row_id)
            if row is None:
                skipped.append({"ip": ip, "reason": "missing_row", "kind": kind, "id": row_id})
                continue
            # Refresh presence; don't overwrite agent-managed hostname aggressively
            if hasattr(row, "last_seen_at"):
                row.last_seen_at = now
            if hasattr(row, "status"):
                row.status = (raw.get("status") or "online").strip().lower() or "online"
            if kind == "computer" and not getattr(row, "agent_id", None):
                if hostname:
                    row.hostname = hostname[:255]
                if os_name:
                    row.os_name = str(os_name)[:120]
            elif kind == "server":
                if hostname:
                    row.hostname = hostname[:255]
                if os_name:
                    row.os_name = str(os_name)[:120]
            elif kind == "printer":
                if hostname and (not row.name or row.name.startswith("host-")):
                    row.name = hostname[:255]
                if raw.get("model") and (not row.model or row.model == "Unknown"):
                    row.model = str(raw.get("model"))[:120]
            elif kind == "network":
                if hostname:
                    row.hostname = hostname[:255]
                if raw.get("vendor") and raw.get("vendor") != "—":
                    row.vendor = str(raw.get("vendor"))[:120]
            updated.append({"ip": ip, "kind": kind, "id": row_id, "hostname": hostname})
            continue

        # Create via same branches as import_hosts
        if dtype == "Server":
            row = Server(
                hostname=hostname[:255],
                ip_address=ip,
                os_name=(os_name or "Unknown")[:120] if os_name else "Unknown",
                status="online",
                last_seen_at=now,
            )
            kind = "server"
        elif dtype == "Printer":
            row = Printer(
                name=hostname[:255],
                ip_address=ip,
                model=(raw.get("model") or "Unknown")[:120],
                status="online",
                last_seen_at=now,
            )
            kind = "printer"
        elif dtype in {"Network", "Router", "Switch", "Firewall"}:
            row = NetworkDevice(
                hostname=hostname[:255],
                ip_address=ip,
                device_type=dtype if dtype != "Network" else "Network",
                vendor=(raw.get("vendor") or None),
                status="online",
                last_seen_at=now,
            )
            kind = "network"
        else:
            row = Computer(
                hostname=hostname[:255],
                ip_address=ip,
                os_name=(os_name or "Unknown")[:120] if os_name else "Unknown",
                status="online",
                last_seen_at=now,
            )
            kind = "computer"

        db.session.add(row)
        db.session.flush()
        created.append({"ip": ip, "kind": kind, "id": row.id, "hostname": hostname})

    db.session.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "created_count": len(created),
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "site_id": site_id,
    }


def apply_printer_telemetry(printers: list[dict[str, Any]], *, site_id: int | None = None) -> dict[str, Any]:
    """Ensure printers exist and apply SNMP-style telemetry from a site connector."""
    created: list[dict] = []
    updated: list[dict] = []
    now = datetime.now(timezone.utc)

    for raw in printers:
        ip = (raw.get("ip") or "").strip()
        if not ip:
            continue
        hostname = (raw.get("name") or raw.get("hostname") or f"printer-{ip.replace('.', '-')}").strip()
        existing = _find_by_ip(ip)
        row: Printer | None = None

        if existing and existing[0] == "printer":
            row = Printer.query.get(existing[1])
        elif existing:
            # IP already used by another kind — skip creating a printer
            updated.append({"ip": ip, "kind": existing[0], "id": existing[1], "note": "ip_owned_by_other_kind"})
            continue
        else:
            row = Printer(
                name=hostname[:255],
                ip_address=ip,
                model=(raw.get("model") or "Unknown")[:120],
                status="online",
                last_seen_at=now,
            )
            db.session.add(row)
            db.session.flush()
            created.append({"ip": ip, "kind": "printer", "id": row.id})

        assert row is not None
        if hostname:
            row.name = hostname[:255]
        if raw.get("model"):
            row.model = str(raw.get("model"))[:120]
        status = (raw.get("status") or "online").strip().lower()
        row.status = status or "online"
        row.last_seen_at = now
        if raw.get("toner_percent") is not None:
            try:
                row.toner_percent = int(raw["toner_percent"])
            except (TypeError, ValueError):
                pass
        if raw.get("paper_percent") is not None:
            try:
                row.paper_percent = int(raw["paper_percent"])
            except (TypeError, ValueError):
                pass
        if raw.get("snmp_sys_descr"):
            row.snmp_sys_descr = str(raw.get("snmp_sys_descr"))[:512]
        if raw.get("snmp_payload") is not None:
            row.snmp_payload = raw.get("snmp_payload")
        if raw.get("snmp_ok") or raw.get("toner_percent") is not None or raw.get("snmp_sys_descr"):
            row.last_snmp_at = now
        updated.append({"ip": ip, "kind": "printer", "id": row.id})

    db.session.commit()
    return {
        "created": created,
        "updated": updated,
        "created_count": len(created),
        "updated_count": len(updated),
        "site_id": site_id,
    }


def _get_inventory_row(kind: str, row_id: int):
    if kind == "computer":
        return Computer.query.get(row_id)
    if kind == "server":
        return Server.query.get(row_id)
    if kind == "printer":
        return Printer.query.get(row_id)
    if kind == "network":
        return NetworkDevice.query.get(row_id)
    return None


def _find_by_ip(ip: str) -> tuple[str, int] | None:
    c = Computer.query.filter_by(ip_address=ip).first()
    if c:
        return ("computer", c.id)
    s = Server.query.filter_by(ip_address=ip).first()
    if s:
        return ("server", s.id)
    p = Printer.query.filter_by(ip_address=ip).first()
    if p:
        return ("printer", p.id)
    n = NetworkDevice.query.filter_by(ip_address=ip).first()
    if n:
        return ("network", n.id)
    return None
