"""Infrastructure Monitoring hub — live agent telemetry + estate mock fill."""
from __future__ import annotations

from uitop.models.agent_telemetry import AgentAlert, AgentEvent, PerformanceSample
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.services.computers_view import (
    derive_presence,
    latest_sample,
    performance_series,
    relative_time,
    serialize_computer,
)
from uitop.services import inventory_view as inv


def _presence_obj(status, agent_id, last_seen_at):
    return type("P", (), {"status": status, "agent_id": agent_id, "last_seen_at": last_seen_at})()


def _avg(values: list[float | int]) -> int:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return 0
    return int(round(sum(nums) / len(nums)))


def _health_label(score: int) -> tuple[str, str]:
    if score >= 95:
        return "Excellent", "success"
    if score >= 85:
        return "Good", "accent"
    if score >= 70:
        return "Fair", "warning"
    return "Poor", "danger"


def live_devices() -> list[dict]:
    """Unified live device rows for Monitoring (computers + servers + network + printers)."""
    rows: list[dict] = []

    for c in Computer.query.order_by(Computer.hostname).all():
        sample = latest_sample(c.id)
        row = serialize_computer(c, sample)
        net = 0
        if sample and (sample.network_bytes_sent or sample.network_bytes_recv):
            net = int(((sample.network_bytes_sent or 0) + (sample.network_bytes_recv or 0)) / 1024)
        rows.append(
            {
                "id": c.id,
                "name": c.hostname,
                "type": "Computer",
                "kind": "computer",
                "status": row["status"],
                "last_seen": row["last_seen"],
                "cpu": row["cpu"],
                "ram": row["ram"],
                "disk": row["disk"],
                "network": net,
                "url": f"/computers/{c.id}?tab=performance",
                "monitor_url": f"/monitoring/{c.id}?kind=computer",
            }
        )

    for s in Server.query.order_by(Server.hostname).all():
        status, _ = derive_presence(_presence_obj(s.status, s.agent_id, s.last_seen_at))
        # Mock performance for servers without samples
        cpu = 42 if status == "Online" else 0
        ram = 68 if status == "Online" else 0
        disk = 55 if status == "Online" else 0
        if status == "Warning":
            cpu, ram = 78, 86
        if status == "Critical":
            cpu, ram = 94, 91
        rows.append(
            {
                "id": s.id,
                "name": s.hostname,
                "type": "Server",
                "kind": "server",
                "status": status,
                "last_seen": relative_time(s.last_seen_at),
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "network": 120 if status == "Online" else 0,
                "url": f"/servers/{s.id}?tab=performance",
                "monitor_url": f"/monitoring/{s.id}?kind=server",
            }
        )

    for n in NetworkDevice.query.order_by(NetworkDevice.hostname).all():
        raw = (n.status or "unknown").lower()
        status = "Online" if raw in {"online", "up"} else ("Warning" if raw == "warning" else "Offline")
        rows.append(
            {
                "id": n.id,
                "name": n.hostname,
                "type": (n.device_type or "Network").title(),
                "kind": "network",
                "status": status,
                "last_seen": relative_time(n.last_seen_at),
                "cpu": 12 if status == "Online" else 0,
                "ram": 28 if status == "Online" else 0,
                "disk": 0,
                "network": 85 if status == "Online" else 0,
                "url": f"/network/{n.id}",
                "monitor_url": f"/monitoring/{n.id}?kind=network",
            }
        )

    for p in Printer.query.order_by(Printer.name).all():
        raw = (p.status or "unknown").lower()
        status = "Online" if raw in {"online", "up"} else ("Warning" if raw == "warning" else "Offline")
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "type": "Printer",
                "kind": "printer",
                "status": status,
                "last_seen": relative_time(p.last_seen_at),
                "cpu": 0,
                "ram": 0,
                "disk": 0,
                "network": 5 if status == "Online" else 0,
                "url": f"/printers/{p.id}",
                "monitor_url": f"/monitoring/{p.id}?kind=printer",
            }
        )

    # Enrich with mock estate if inventory is tiny (demo feel)
    if len(rows) < 8:
        rows.extend(_mock_extra_devices(len(rows)))

    return rows


def _mock_extra_devices(start_id: int) -> list[dict]:
    extras = [
        ("CORE-SW-01", "Switch", "Online", 8, 22, 0, 240),
        ("FW-EDGE-01", "Firewall", "Online", 15, 40, 0, 180),
        ("AP-FIN-03", "Access Point", "Warning", 5, 18, 0, 60),
        ("HV-CLUS-01", "Server", "Online", 55, 72, 61, 200),
    ]
    out = []
    for i, (name, typ, status, cpu, ram, disk, net) in enumerate(extras, start=9000 + start_id):
        kind = "network" if typ in {"Switch", "Firewall", "Access Point"} else "server"
        out.append(
            {
                "id": i,
                "name": name,
                "type": typ,
                "kind": kind,
                "status": status,
                "last_seen": "2 mins ago",
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "network": net,
                "url": "/network/" if kind == "network" else "/servers/",
                "monitor_url": f"/monitoring/{i}?kind={kind}",
                "demo": True,
            }
        )
    return out


def estate_averages(devices: list[dict]) -> dict:
    online = [d for d in devices if d["status"] == "Online"]
    endpoints = [d for d in devices if d["kind"] in {"computer", "server"} and d["status"] != "Offline"]
    return {
        "cpu": _avg([d["cpu"] for d in endpoints]) or 34,
        "ram": _avg([d["ram"] for d in endpoints]) or 58,
        "disk": _avg([d["disk"] for d in endpoints if d.get("disk")]) or 71,
        "network": 99 if online else 72,
    }


def compute_health_score(devices: list[dict], alerts: list[dict]) -> int:
    total = max(1, len(devices))
    offline = sum(1 for d in devices if d["status"] == "Offline")
    high_cpu = sum(1 for d in devices if d.get("cpu", 0) >= 90)
    high_disk = sum(1 for d in devices if d.get("disk", 0) >= 90)
    critical = sum(1 for a in alerts if a.get("severity") in {"critical", "error"} and a.get("status") == "open")
    warnings = sum(1 for a in alerts if a.get("severity") == "warning" and a.get("status") == "open")

    score = 100
    score -= int((offline / total) * 40)
    score -= min(20, high_cpu * 3)
    score -= min(15, high_disk * 3)
    score -= min(15, critical * 5)
    score -= min(10, warnings * 1)
    return max(0, min(100, score))


def serialize_alert(a: AgentAlert) -> dict:
    host = a.computer.hostname if a.computer else (a.agent_id or "Unknown")
    return {
        "id": a.id,
        "title": a.title,
        "message": a.message or "",
        "severity": a.severity,
        "status": a.status,
        "code": a.alert_code,
        "host": host,
        "computer_id": a.computer_id,
        "when": relative_time(a.occurred_at),
        "occurred_at": a.occurred_at.isoformat() if a.occurred_at else None,
        "url": f"/computers/{a.computer_id}?tab=alerts" if a.computer_id else "/monitoring/?view=alerts",
        "actions": _recommended_actions(a.alert_code, a.severity),
    }


def _recommended_actions(code: str, severity: str) -> list[dict]:
    code = (code or "").lower()
    actions = [
        {"label": "View device", "icon": "fa-desktop"},
        {"label": "View processes", "icon": "fa-list"},
    ]
    if "cpu" in code or "memory" in code or "mem" in code:
        actions.insert(0, {"label": "Restart service", "icon": "fa-rotate"})
    if "disk" in code:
        actions.insert(0, {"label": "Free disk space", "icon": "fa-hard-drive"})
    if "offline" in code or severity == "critical":
        actions.insert(0, {"label": "Remote connect", "icon": "fa-plug"})
    return actions[:4]


def list_alerts(*, limit: int = 40) -> list[dict]:
    rows = (
        AgentAlert.query.order_by(AgentAlert.occurred_at.desc()).limit(limit).all()
    )
    alerts = [serialize_alert(a) for a in rows]
    if len(alerts) < 5:
        alerts.extend(_mock_alerts())
    return alerts


def _mock_alerts() -> list[dict]:
    return [
        {
            "id": 9001,
            "title": "CPU above 90%",
            "message": "Sustained high CPU on APP-ERP-02 for 12 minutes.",
            "severity": "critical",
            "status": "open",
            "code": "cpu_high",
            "host": "APP-ERP-02",
            "computer_id": None,
            "when": "18 mins ago",
            "occurred_at": None,
            "url": "/servers/",
            "actions": _recommended_actions("cpu_high", "critical"),
            "demo": True,
        },
        {
            "id": 9002,
            "title": "Disk below 10GB free",
            "message": "System volume on FIN-LAP-14 is critically low.",
            "severity": "warning",
            "status": "open",
            "code": "disk_low",
            "host": "FIN-LAP-14",
            "computer_id": None,
            "when": "42 mins ago",
            "occurred_at": None,
            "url": "/computers/",
            "actions": _recommended_actions("disk_low", "warning"),
            "demo": True,
        },
        {
            "id": 9003,
            "title": "Printer offline",
            "message": "Finance HP LaserJet stopped responding.",
            "severity": "warning",
            "status": "open",
            "code": "printer_offline",
            "host": "PRT-FIN-01",
            "computer_id": None,
            "when": "1 hr ago",
            "occurred_at": None,
            "url": "/printers/",
            "actions": [
                {"label": "Restart spooler", "icon": "fa-print"},
                {"label": "Open printer", "icon": "fa-arrow-up-right-from-square"},
            ],
            "demo": True,
        },
        {
            "id": 9004,
            "title": "Antivirus disabled",
            "message": "EDR service not reporting on CORP-PC-08.",
            "severity": "critical",
            "status": "open",
            "code": "av_disabled",
            "host": "CORP-PC-08",
            "computer_id": None,
            "when": "2 hrs ago",
            "occurred_at": None,
            "url": "/computers/",
            "actions": _recommended_actions("av_disabled", "critical"),
            "demo": True,
        },
        {
            "id": 9005,
            "title": "Windows Update failed",
            "message": "KB5039212 failed on 6 endpoints overnight.",
            "severity": "warning",
            "status": "open",
            "code": "update_failed",
            "host": "Multiple",
            "computer_id": None,
            "when": "5 hrs ago",
            "occurred_at": None,
            "url": "/computers/",
            "actions": [{"label": "View affected", "icon": "fa-list"}, {"label": "Retry deploy", "icon": "fa-rotate"}],
            "demo": True,
        },
    ]


def list_events(*, limit: int = 30) -> list[dict]:
    rows = AgentEvent.query.order_by(AgentEvent.occurred_at.desc()).limit(limit).all()
    events = []
    for e in rows:
        events.append(
            {
                "id": e.id,
                "type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "host": e.computer.hostname if e.computer else e.agent_id,
                "when": relative_time(e.occurred_at),
                "source": e.source or "Agent",
            }
        )
    if len(events) < 6:
        events.extend(
            [
                {"id": 8001, "type": "cpu_high", "severity": "warning", "message": "CPU High on APP-ERP-02", "host": "APP-ERP-02", "when": "10:12", "source": "Monitor"},
                {"id": 8002, "type": "memory_high", "severity": "warning", "message": "Memory High on APP-ERP-02", "host": "APP-ERP-02", "when": "10:15", "source": "Monitor"},
                {"id": 8003, "type": "disk_full", "severity": "error", "message": "Disk Full warning on FIN-LAP-14", "host": "FIN-LAP-14", "when": "10:20", "source": "Monitor"},
                {"id": 8004, "type": "resolved", "severity": "info", "message": "CPU pressure resolved after service recycle", "host": "APP-ERP-02", "when": "10:30", "source": "Technician"},
                {"id": 8005, "type": "agent", "severity": "info", "message": "Agent heartbeat resumed", "host": "CORP-PC-02", "when": "10:41", "source": "Agent"},
                {"id": 8006, "type": "service", "severity": "warning", "message": "Print Spooler restarted remotely", "host": "PRT-FIN-01", "when": "11:02", "source": "Remote"},
            ]
        )
    return events


def services_snapshot() -> list[dict]:
    return [
        {"name": "Print Spooler", "host": "PRT-FIN-01", "status": "Running", "type": "Windows"},
        {"name": "SQL Server (MSSQLSERVER)", "host": "SQL-PROD-01", "status": "Stopped", "type": "Database"},
        {"name": "DHCP Server", "host": "DC-AD-01", "status": "Running", "type": "Network"},
        {"name": "DNS Server", "host": "DC-AD-01", "status": "Running", "type": "Network"},
        {"name": "Windows Update", "host": "APP-ERP-02", "status": "Running", "type": "System"},
        {"name": "UITOP Agent", "host": "Fleet", "status": "Running", "type": "Agent"},
        {"name": "IIS Admin Service", "host": "WEB-INTRA-01", "status": "Running", "type": "Web"},
        {"name": "CrowdStrike Falcon", "host": "Fleet", "status": "Running", "type": "Security"},
    ]


def processes_snapshot() -> list[dict]:
    return [
        {"name": "sqlservr.exe", "host": "SQL-PROD-01", "cpu": 25, "ram": 18, "user": "SYSTEM"},
        {"name": "chrome.exe", "host": "FIN-LAP-14", "cpu": 12, "ram": 9, "user": "finance.user"},
        {"name": "Teams.exe", "host": "CORP-PC-08", "cpu": 8, "ram": 11, "user": "corp.user"},
        {"name": "w3wp.exe", "host": "WEB-INTRA-01", "cpu": 14, "ram": 7, "user": "IIS APPPOOL"},
        {"name": "MsMpEng.exe", "host": "DC-AD-01", "cpu": 3, "ram": 4, "user": "SYSTEM"},
        {"name": "UITOPAgent.exe", "host": "Fleet", "cpu": 1, "ram": 2, "user": "SYSTEM"},
    ]


def network_snapshot() -> list[dict]:
    return [
        {"name": "CORE-SW-01", "role": "Core Switch", "status": "Online", "bandwidth": "1.2 Gbps", "latency": "1 ms", "loss": "0%", "ports_up": "44/48"},
        {"name": "FW-EDGE-01", "role": "Edge Firewall", "status": "Online", "bandwidth": "420 Mbps", "latency": "3 ms", "loss": "0%", "ports_up": "8/8"},
        {"name": "AP-FIN-03", "role": "Access Point", "status": "Warning", "bandwidth": "86 Mbps", "latency": "18 ms", "loss": "1.2%", "ports_up": "—"},
        {"name": "DIST-SW-02", "role": "Distribution", "status": "Online", "bandwidth": "640 Mbps", "latency": "2 ms", "loss": "0%", "ports_up": "22/24"},
    ]


def ai_insights(devices: list[dict], alerts: list[dict]) -> list[dict]:
    insights = [
        {
            "title": "CPU trend on application servers",
            "finding": "Server CPU has been elevated for 3 consecutive days during business hours.",
            "cause": "Likely overlapping SQL backup / reporting jobs.",
            "recommendation": "Move backup schedule to midnight and review index maintenance windows.",
            "tone": "warning",
        },
        {
            "title": "Recurring printer offline pattern",
            "finding": "Finance printers go offline most Mondays around 08:00.",
            "cause": "Possible weekend switch port power-save or firmware hang.",
            "recommendation": "Check POE schedule on CORE-SW-01 and update printer firmware.",
            "tone": "accent",
        },
        {
            "title": "Disk pressure cluster",
            "finding": "Several laptops are trending above 85% disk usage.",
            "cause": "Local Outlook OST growth and Windows update cache.",
            "recommendation": "Push disk cleanup policy and OneDrive Known Folder Move.",
            "tone": "success",
        },
    ]
    hot = sorted([d for d in devices if d["kind"] in {"computer", "server"}], key=lambda d: d.get("cpu", 0), reverse=True)
    if hot and hot[0]["cpu"] >= 70:
        insights.insert(
            0,
            {
                "title": f"Live pressure on {hot[0]['name']}",
                "finding": f"Current CPU {hot[0]['cpu']}% · RAM {hot[0]['ram']}%.",
                "cause": "Active workload or runaway process.",
                "recommendation": "Open live performance, inspect top processes, restart non-critical services.",
                "tone": "danger",
                "url": hot[0].get("url"),
            },
        )
    return insights


def performance_fleet_series() -> dict:
    """Aggregate last samples across computers for overview sparkline-style charts."""
    labels = []
    cpu, mem, disk = [], [], []
    # Use most recent samples globally
    samples = (
        PerformanceSample.query.order_by(PerformanceSample.collected_at.desc()).limit(60).all()
    )
    samples.reverse()
    if samples:
        for s in samples:
            labels.append(s.collected_at.strftime("%H:%M") if s.collected_at else "")
            cpu.append(round(s.cpu_percent or 0, 1))
            mem.append(round(s.memory_percent or 0, 1))
            disk.append(round(s.disk_percent or 0, 1))
    else:
        labels = ["-55m", "-45m", "-35m", "-25m", "-15m", "-5m", "now"]
        cpu = [28, 32, 40, 36, 44, 38, 34]
        mem = [50, 52, 55, 58, 60, 57, 58]
        disk = [68, 69, 70, 70, 71, 71, 71]
    return {"labels": labels, "cpu": cpu, "mem": mem, "disk": disk}


def build_module_payload() -> dict:
    devices = live_devices()
    alerts = list_alerts()
    avgs = estate_averages(devices)
    health = compute_health_score(devices, alerts)
    health_label, health_tone = _health_label(health)

    online = sum(1 for d in devices if d["status"] == "Online")
    offline = sum(1 for d in devices if d["status"] == "Offline")
    critical_alerts = sum(1 for a in alerts if a["severity"] in {"critical", "error"} and a["status"] == "open")
    warning_alerts = sum(1 for a in alerts if a["severity"] == "warning" and a["status"] == "open")

    computers = [d for d in devices if d["kind"] == "computer"]
    servers = [d for d in devices if d["kind"] == "server"]
    printers = [d for d in devices if d["kind"] == "printer"]
    network = [d for d in devices if d["kind"] == "network"]

    def _online_count(rows):
        return sum(1 for r in rows if r["status"] == "Online")

    return {
        "kpis": {
            "health": health,
            "health_label": health_label,
            "health_tone": health_tone,
            "online": online,
            "offline": offline,
            "critical_alerts": critical_alerts,
            "warnings": warning_alerts,
            "cpu_avg": avgs["cpu"],
            "ram_avg": avgs["ram"],
            "disk_avg": avgs["disk"],
            "network_health": avgs["network"],
            "servers_online": _online_count(servers),
            "servers_total": len(servers) or 42,
            "computers_online": _online_count(computers),
            "computers_total": len(computers) or 184,
            "printers_online": _online_count(printers),
            "printers_total": len(printers) or 28,
            "network_online": _online_count(network),
            "network_total": len(network) or 15,
        },
        "devices": devices,
        "alerts": alerts,
        "events": list_events(),
        "services": services_snapshot(),
        "processes": processes_snapshot(),
        "network_devices": network_snapshot(),
        "ai_insights": ai_insights(devices, alerts),
        "series": performance_fleet_series(),
        "reports": [
            {"name": "Performance summary", "desc": "CPU / RAM / Disk by device class", "format": "PDF"},
            {"name": "Availability (30 days)", "desc": "Uptime % for servers and core network", "format": "Excel"},
            {"name": "Downtime incidents", "desc": "Offline windows and MTTR", "format": "PDF"},
            {"name": "Top CPU devices", "desc": "Highest average CPU this week", "format": "Excel"},
            {"name": "Storage usage", "desc": "Volumes above 80% capacity", "format": "PDF"},
            {"name": "Network usage", "desc": "Bandwidth and loss by site", "format": "Excel"},
        ],
        "refresh_seconds": 20,
    }


def build_device_payload(item_id: int, kind: str | None = None) -> dict | None:
    kind = (kind or "computer").lower()
    if kind == "computer":
        computer = Computer.query.get(item_id)
        if not computer:
            return None
        sample = latest_sample(computer.id)
        device = serialize_computer(computer, sample)
        return {
            "kind": "computer",
            "device": device,
            "series": performance_series(item_id),
            "alerts": [serialize_alert(a) for a in AgentAlert.query.filter_by(computer_id=item_id).order_by(AgentAlert.occurred_at.desc()).limit(20)],
            "events": [
                {
                    "type": e.event_type,
                    "severity": e.severity,
                    "message": e.message,
                    "when": relative_time(e.occurred_at),
                }
                for e in AgentEvent.query.filter_by(computer_id=item_id).order_by(AgentEvent.occurred_at.desc()).limit(20)
            ],
            "services": services_snapshot()[:5],
            "processes": processes_snapshot()[:6],
            "infra_url": f"/computers/{item_id}",
        }

    if kind == "server":
        row = Server.query.get(item_id)
        if not row:
            # Allow demo IDs
            return {
                "kind": "server",
                "device": {
                    "id": item_id,
                    "name": f"SRV-DEMO-{item_id}",
                    "hostname": f"SRV-DEMO-{item_id}",
                    "status": "Online",
                    "cpu": 55,
                    "ram": 72,
                    "disk": 61,
                    "ip": "10.10.10.20",
                    "last_seen": "2 mins ago",
                },
                "series": {"labels": ["-30m", "-20m", "-10m", "now"], "cpu": [40, 48, 62, 55], "mem": [60, 65, 70, 72], "disk": [58, 59, 60, 61]},
                "alerts": list_alerts()[:3],
                "events": list_events()[:5],
                "services": services_snapshot(),
                "processes": processes_snapshot(),
                "infra_url": "/servers/",
            }
        ser = inv.serialize_server(row)
        return {
            "kind": "server",
            "device": ser,
            "series": {"labels": ["-30m", "-20m", "-10m", "now"], "cpu": [30, 40, 50, ser.get("cpu", 40)], "mem": [50, 60, 70, ser.get("ram", 60)], "disk": [40, 45, 50, ser.get("disk", 50)]},
            "alerts": [a for a in list_alerts() if a.get("host") == row.hostname][:5] or list_alerts()[:2],
            "events": list_events()[:6],
            "services": services_snapshot(),
            "processes": processes_snapshot(),
            "infra_url": f"/servers/{item_id}",
        }

    # network / printer — lightweight
    return {
        "kind": kind,
        "device": {
            "id": item_id,
            "name": f"{kind.upper()}-{item_id}",
            "hostname": f"{kind.upper()}-{item_id}",
            "status": "Online",
            "cpu": 10,
            "ram": 20,
            "disk": 0,
            "ip": "—",
            "last_seen": "Just now",
        },
        "series": performance_fleet_series(),
        "alerts": list_alerts()[:2],
        "events": list_events()[:4],
        "services": [],
        "processes": [],
        "infra_url": f"/{'network' if kind == 'network' else 'printers'}/",
    }
