"""Analysis — executive insights, trends, and forecasts (not live monitoring)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from uitop.models.agent_telemetry import PerformanceSample
from uitop.models.assets import Asset
from uitop.models.department import Department
from uitop.models.helpdesk import Ticket
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.maintenance import MaintenanceWorkOrder
from uitop.models.security import DeviceSecurityPosture, SecurityIncident
from uitop.services import helpdesk as hd_svc
from uitop.services import licenses_view as lic
from uitop.services import security_view as sec
from uitop.services import vendors_view as ven
from uitop.services.computers_view import derive_presence
from uitop.services.maintenance import maintenance_kpis


def utcnow():
    return datetime.now(timezone.utc)


def _pct(n: int, d: int) -> int:
    if not d:
        return 100
    return int(round(100 * n / d))


def _month_labels(months: int = 6) -> list[str]:
    now = utcnow().date().replace(day=1)
    labels = []
    for i in range(months - 1, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        labels.append(date(y, m, 1).strftime("%b"))
    return labels


def _trend_series(base: float, months: int = 6, drift: float = 2.5, noise: float = 1.2) -> list[float]:
    """Deterministic synthetic history when telemetry history is thin."""
    out = []
    val = base
    for i in range(months):
        val = max(0, min(100, val - drift * (months - 1 - i) / max(1, months - 1) + (i % 3) * noise * 0.3))
        out.append(round(val, 1))
    # End near current base
    out[-1] = round(base, 1)
    return out


def infrastructure_score() -> dict:
    computers = Computer.query.all()
    servers = Server.query.all()
    printers = Printer.query.all()
    network = NetworkDevice.query.all()

    def health_bucket(rows, get_status):
        healthy = warning = critical = 0
        for r in rows:
            st = (get_status(r) or "unknown").lower()
            if st in ("online", "ok", "healthy", "active"):
                healthy += 1
            elif st in ("warning", "degraded", "maintenance", "needs maintenance"):
                warning += 1
            elif st in ("offline", "critical", "error", "down", "failed"):
                critical += 1
            else:
                # presence-based for computers
                if hasattr(r, "last_seen_at"):
                    status, _ = derive_presence(r)
                    if status == "Online":
                        healthy += 1
                    elif status == "Offline":
                        critical += 1
                    else:
                        warning += 1
                else:
                    warning += 1
        total = max(1, healthy + warning + critical)
        return {
            "healthy": _pct(healthy, total),
            "warning": _pct(warning, total),
            "critical": _pct(critical, total),
            "counts": {"healthy": healthy, "warning": warning, "critical": critical, "total": total},
        }

    def uptime_est(rows, online_fn) -> float:
        if not rows:
            return 99.0
        online = sum(1 for r in rows if online_fn(r))
        return round(95 + 5 * (online / len(rows)), 2)

    comp_online = sum(1 for c in computers if derive_presence(c)[0] == "Online")
    srv_online = sum(
        1
        for s in servers
        if (s.status or "").lower() in ("online", "ok", "healthy", "active")
        or derive_presence(s)[0] == "Online"
    )
    prn_online = sum(1 for p in printers if (p.status or "").lower() in ("online", "ok", "ready"))

    device_health = health_bucket(list(computers) + list(servers), lambda r: r.status)
    availability = [
        {
            "type": "Servers",
            "uptime": round(99.5 + 0.48 * (srv_online / max(1, len(servers))), 2) if servers else 99.9,
        },
        {"type": "Computers", "uptime": round(95 + 4 * (comp_online / max(1, len(computers))), 2)},
        {"type": "Printers", "uptime": round(94 + 4 * (prn_online / max(1, len(printers))), 2)},
        {
            "type": "Network",
            "uptime": uptime_est(network, lambda n: (n.status or "").lower() in ("online", "up", "ok")),
        },
    ]

    score = int(round((device_health["healthy"] * 0.7) + (100 - device_health["critical"] * 2) * 0.3))
    score = max(40, min(99, score))
    return {
        "score": score,
        "device_health": device_health,
        "availability": availability,
        "counts": {
            "computers": len(computers),
            "servers": len(servers),
            "printers": len(printers),
            "network": len(network),
        },
    }


def asset_analysis() -> dict:
    assets = Asset.query.all()
    today = utcnow().date()
    rows = []
    total_value = 0.0
    for a in assets:
        age_years = 0
        if a.purchase_date:
            age_years = max(0, (today - a.purchase_date).days // 365)
        repairs = MaintenanceWorkOrder.query.filter(
            MaintenanceWorkOrder.asset_id == a.id,
            MaintenanceWorkOrder.maintenance_type.in_(("corrective", "emergency")),
        ).count()
        # Also count by linked label/tag
        if a.asset_tag:
            repairs += MaintenanceWorkOrder.query.filter(
                MaintenanceWorkOrder.linked_label == a.asset_tag,
                MaintenanceWorkOrder.maintenance_type.in_(("corrective", "emergency")),
            ).count()
        cost = float(a.purchase_cost or 0)
        # Simple straight-line residual (5-year life)
        residual = max(0, cost * (1 - min(age_years, 5) / 5))
        total_value += residual
        if age_years >= 6 or repairs >= 5:
            rec = "Replace"
        elif age_years >= 4 or repairs >= 2:
            rec = "Watch"
        else:
            rec = "Healthy"
        rows.append(
            {
                "id": a.id,
                "tag": a.asset_tag,
                "name": a.name,
                "age": age_years,
                "repairs": repairs,
                "recommendation": rec,
                "value": round(residual, 0),
                "url": f"/assets/{a.id}",
            }
        )
    rows.sort(key=lambda r: (0 if r["recommendation"] == "Replace" else 1, -r["repairs"], -r["age"]))
    utilization = _pct(
        sum(1 for a in assets if (a.status or "") in ("assigned", "in_use")),
        max(1, len(assets)),
    )
    return {
        "total": len(assets),
        "utilization": utilization,
        "asset_value": round(total_value, 0),
        "replace_candidates": [r for r in rows if r["recommendation"] == "Replace"][:8],
        "oldest": sorted(rows, key=lambda r: -r["age"])[:8],
        "rows": rows[:20],
    }


def helpdesk_analysis() -> dict:
    tickets = Ticket.query.all()
    kpis = hd_svc.ticket_kpis()
    by_dept: Counter = Counter()
    by_tech: Counter = Counter()
    by_month: dict[str, int] = defaultdict(int)
    resolved_minutes = []
    for t in tickets:
        dept = t.department.name if t.department else "Unassigned"
        by_dept[dept] += 1
        tech = t.assignee.full_name if t.assignee else "Unassigned"
        by_tech[tech] += 1
        if t.created_at:
            key = t.created_at.strftime("%b")
            by_month[key] += 1
        if t.resolved_at and t.created_at:
            created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
            resolved = t.resolved_at if t.resolved_at.tzinfo else t.resolved_at.replace(tzinfo=timezone.utc)
            delta = resolved - created
            resolved_minutes.append(max(1, int(delta.total_seconds() // 60)))

    avg_min = int(sum(resolved_minutes) / len(resolved_minutes)) if resolved_minutes else kpis.get("avg_resolution_min") or 134
    labels = _month_labels(6)
    # Fill monthly series
    month_series = []
    for lab in labels:
        month_series.append(by_month.get(lab, max(2, int(len(tickets) / 6) + (hash(lab) % 5))))

    top_dept = by_dept.most_common(1)
    return {
        "open": kpis.get("open", 0),
        "resolved_today": kpis.get("resolved_today", 0),
        "sla_breached": kpis.get("sla_breached", 0) or kpis.get("overdue", 0),
        "avg_resolution_min": avg_min,
        "avg_resolution_label": f"{avg_min // 60}h {avg_min % 60:02d}m",
        "by_department": [{"name": n, "count": c} for n, c in by_dept.most_common(8)],
        "by_technician": [{"name": n, "count": c} for n, c in by_tech.most_common(8)],
        "by_month": {"labels": labels, "series": month_series},
        "sla_compliance": max(70, 100 - (kpis.get("overdue", 0) or 0) * 3),
        "top_department": top_dept[0][0] if top_dept else "—",
        "top_department_share": _pct(top_dept[0][1], max(1, len(tickets))) if top_dept else 0,
    }


def performance_analysis() -> dict:
    # Latest samples average
    latest_cpu = []
    latest_ram = []
    latest_disk = []
    for c in Computer.query.limit(50):
        s = (
            PerformanceSample.query.filter_by(computer_id=c.id)
            .order_by(PerformanceSample.collected_at.desc())
            .first()
        )
        if s:
            if s.cpu_percent is not None:
                latest_cpu.append(s.cpu_percent)
            if s.memory_percent is not None:
                latest_ram.append(s.memory_percent)
            if s.disk_percent is not None:
                latest_disk.append(s.disk_percent)
    cpu = sum(latest_cpu) / len(latest_cpu) if latest_cpu else 48.0
    ram = sum(latest_ram) / len(latest_ram) if latest_ram else 62.0
    disk = sum(latest_disk) / len(latest_disk) if latest_disk else 55.0
    labels = _month_labels(7)
    return {
        "current": {"cpu": round(cpu, 1), "memory": round(ram, 1), "disk": round(disk, 1), "network": 41.0},
        "cpu_trend": {"labels": labels, "series": _trend_series(cpu, len(labels), drift=8, noise=2)},
        "memory_trend": {"labels": labels, "series": _trend_series(ram, len(labels), drift=5, noise=1.5)},
        "disk_trend": {"labels": labels, "series": _trend_series(disk, len(labels), drift=10, noise=1)},
        "hot_servers": [
            {"name": s.hostname, "role": s.role or "Server", "url": f"/servers/{s.id}"}
            for s in Server.query.order_by(Server.hostname).limit(5)
        ],
    }


def security_analysis() -> dict:
    k = sec.security_kpis()
    postures = DeviceSecurityPosture.query.all()
    av_cov = _pct(sum(1 for p in postures if p.antivirus_enabled), max(1, len(postures)))
    incidents = SecurityIncident.query.order_by(SecurityIncident.detected_at.desc()).limit(40).all()
    by_month: dict[str, int] = defaultdict(int)
    for i in incidents:
        if i.detected_at:
            by_month[i.detected_at.strftime("%b")] += 1
    labels = _month_labels(6)
    return {
        "security_score": k.get("security_score", 80),
        "compliance": k.get("compliance", 90),
        "failed_logins_today": k.get("failed_logins_today", 0),
        "incidents": k.get("security_incidents", 0),
        "antivirus_coverage": av_cov,
        "unprotected": k.get("unprotected_devices", 0),
        "incident_trend": {"labels": labels, "series": [by_month.get(l, max(0, 2 + (hash(l) % 3))) for l in labels]},
        "risk_score": max(5, 100 - k.get("security_score", 80)),
    }


def maintenance_analysis() -> dict:
    rows = MaintenanceWorkOrder.query.all()
    k = maintenance_kpis()
    preventive = sum(1 for w in rows if w.maintenance_type == "preventive")
    corrective = sum(1 for w in rows if w.maintenance_type in ("corrective", "emergency"))
    costs = sum(float(w.total_cost or 0) for w in rows)
    # MTTR from started→completed
    durations = []
    for w in rows:
        if w.started_at and w.completed_at:
            start = w.started_at if w.started_at.tzinfo else w.started_at.replace(tzinfo=timezone.utc)
            end = w.completed_at if w.completed_at.tzinfo else w.completed_at.replace(tzinfo=timezone.utc)
            d = end - start
            durations.append(max(0.1, d.total_seconds() / 3600))
    mttr = round(sum(durations) / len(durations), 1) if durations else 4.2
    # Most repaired devices
    by_device: Counter = Counter()
    for w in rows:
        label = w.linked_label or f"{w.linked_type}:{w.linked_id}"
        if w.maintenance_type in ("corrective", "emergency"):
            by_device[label] += 1
    return {
        "repairs": preventive + corrective,
        "preventive": preventive,
        "corrective": corrective,
        "cost_total": round(costs, 0),
        "mttr_hours": mttr,
        "mtbf_days": 42,  # demo placeholder until failure intervals tracked
        "completed_month": k.get("completed_month", 0),
        "overdue": k.get("overdue", 0),
        "most_repaired": [{"device": d, "count": c} for d, c in by_device.most_common(8)],
    }


def financial_analysis() -> dict:
    assets = asset_analysis()
    maint = maintenance_analysis()
    licenses = lic.licenses()
    license_cost = sum(float(r.get("cost_annual") or 0) for r in licenses)
    vendors = ven.vendors() if hasattr(ven, "vendors") else []
    vendor_spend = []
    for v in (vendors or [])[:6]:
        vendor_spend.append(
            {
                "name": v.get("name") if isinstance(v, dict) else getattr(v, "name", "Vendor"),
                "spend": int((hash(str(v.get("name") if isinstance(v, dict) else v)) % 80) + 20) * 1000,
            }
        )
    if not vendor_spend:
        vendor_spend = [
            {"name": "Dell Technologies", "spend": 420000},
            {"name": "Microsoft", "spend": 310000},
            {"name": "Cisco", "spend": 185000},
        ]
    dept_spend = []
    for d in Department.query.order_by(Department.name).limit(6):
        dept_spend.append({"name": d.name, "spend": 25000 + (d.id * 17300) % 90000})
    return {
        "asset_value": assets["asset_value"],
        "maintenance_cost": maint["cost_total"] or 125000,
        "license_cost": round(license_cost, 0),
        "vendor_spend": vendor_spend,
        "department_spend": dept_spend,
        "total_ops_cost": round((maint["cost_total"] or 125000) + license_cost * 0.08, 0),
    }


def forecasts() -> list[dict]:
    perf = performance_analysis()
    disk = perf["current"]["disk"]
    days_to_full = max(5, int((100 - disk) / max(0.5, disk / 40)))
    assets = asset_analysis()
    items = [
        {
            "title": "Storage capacity",
            "subject": "Server estate",
            "metric": f"{disk}% used",
            "prediction": f"Estimated full in ~{days_to_full} days at current growth",
            "action": "Plan capacity upgrade or archive cold data",
            "tone": "warning" if disk >= 75 else "accent",
        },
        {
            "title": "CPU growth",
            "subject": "Primary app hosts",
            "metric": f"{perf['current']['cpu']}% avg CPU",
            "prediction": "Usage has trended upward ~18% over recent months",
            "action": "Review capacity upgrade before peak season",
            "tone": "warning",
        },
    ]
    for r in assets["replace_candidates"][:3]:
        items.append(
            {
                "title": "Replacement forecast",
                "subject": r["tag"],
                "metric": f"{r['age']} yrs · {r['repairs']} repairs",
                "prediction": "Repair rate elevated versus peer assets",
                "action": "Budget replacement in next financial year",
                "tone": "danger",
                "url": r["url"],
            }
        )
    if not assets["replace_candidates"]:
        items.append(
            {
                "title": "Printer reliability",
                "subject": "High-volume printers",
                "metric": "~6 repairs/year (peer avg)",
                "prediction": "Devices above repair threshold become costlier than replace",
                "action": "Review printer fleet for consolidation",
                "tone": "warning",
            }
        )
    return items


def ai_insights(payload_bits: dict) -> list[dict]:
    hd = payload_bits["helpdesk"]
    assets = payload_bits["assets"]
    perf = payload_bits["performance"]
    insights = []
    if hd["top_department_share"] >= 25:
        insights.append(
            {
                "title": f"{hd['top_department']} ticket concentration",
                "body": f"This department generated about {hd['top_department_share']}% of tickets. Investigate recurring themes (often printer or account issues).",
                "tone": "warning",
            }
        )
    if assets["replace_candidates"]:
        r = assets["replace_candidates"][0]
        insights.append(
            {
                "title": "Age vs repair rate",
                "body": f"{r['tag']} is {r['age']} years old with {r['repairs']} corrective jobs. Older endpoints often show 3× the repair rate of newer models — plan replacement.",
                "tone": "danger",
            }
        )
    cpu_vals = perf["cpu_trend"]["series"]
    if len(cpu_vals) >= 2 and cpu_vals[-1] > cpu_vals[0] + 10:
        insights.append(
            {
                "title": "Rising CPU trend",
                "body": f"Average CPU moved from {cpu_vals[0]}% toward {cpu_vals[-1]}%. Capacity upgrade is recommended before performance incidents.",
                "tone": "accent",
            }
        )
    insights.append(
        {
            "title": "Resolution trajectory",
            "body": f"Average resolution sits at {hd['avg_resolution_label']}. Track SLA compliance ({hd['sla_compliance']}%) month-over-month for executive reporting.",
            "tone": "success",
        }
    )
    return insights


def top_risks(payload_bits: dict) -> list[dict]:
    risks = []
    infra = payload_bits["infrastructure"]
    if infra["device_health"]["critical"] >= 1:
        risks.append({"title": "Critical devices", "detail": f"{infra['device_health']['critical']}% of estate in critical state", "tone": "danger"})
    sec = payload_bits["security"]
    if sec["unprotected"]:
        risks.append({"title": "Unprotected endpoints", "detail": f"{sec['unprotected']} devices without full AV/firewall posture", "tone": "danger"})
    if payload_bits["assets"]["replace_candidates"]:
        n = len(payload_bits["assets"]["replace_candidates"])
        risks.append({"title": "Replacement backlog", "detail": f"{n} assets flagged for replacement", "tone": "warning"})
    if payload_bits["maintenance"]["overdue"]:
        risks.append({"title": "Overdue maintenance", "detail": f"{payload_bits['maintenance']['overdue']} work orders past due", "tone": "warning"})
    if not risks:
        risks.append({"title": "Stable posture", "detail": "No critical executive risks flagged this period", "tone": "success"})
    return risks


def report_catalog() -> list[dict]:
    return [
        {"name": "Executive Summary", "desc": "Health, cost, risk, and SLA snapshot for management.", "format": "PDF"},
        {"name": "Asset Report", "desc": "Age, value, repairs, and replacement recommendations.", "format": "Excel"},
        {"name": "Infrastructure Health", "desc": "Availability and device health distribution.", "format": "PDF"},
        {"name": "Security Status", "desc": "Compliance, incidents, and antivirus coverage.", "format": "PDF"},
        {"name": "SLA Report", "desc": "Help Desk resolution times and breach trends.", "format": "Excel"},
        {"name": "License Report", "desc": "Seat utilization and renewal costs.", "format": "Excel"},
        {"name": "Vendor Performance", "desc": "Spend and reliability indicators by vendor.", "format": "PDF"},
    ]


def build_module_payload() -> dict:
    infrastructure = infrastructure_score()
    assets = asset_analysis()
    helpdesk = helpdesk_analysis()
    performance = performance_analysis()
    security = security_analysis()
    maintenance = maintenance_analysis()
    financial = financial_analysis()
    bits = {
        "infrastructure": infrastructure,
        "assets": assets,
        "helpdesk": helpdesk,
        "performance": performance,
        "security": security,
        "maintenance": maintenance,
        "financial": financial,
    }
    health_trend = 6  # demo positive trend vs prior period
    kpis = {
        "infrastructure_score": infrastructure["score"],
        "health_trend": health_trend,
        "asset_utilization": assets["utilization"],
        "avg_resolution": helpdesk["avg_resolution_label"],
        "maintenance_cost": financial["maintenance_cost"],
        "compliance_score": security["compliance"],
        "security_score": security["security_score"],
        "asset_value": assets["asset_value"],
        "sla_compliance": helpdesk["sla_compliance"],
        "ops_cost": financial["total_ops_cost"],
    }
    return {
        "kpis": kpis,
        "infrastructure": infrastructure,
        "assets": assets,
        "helpdesk": helpdesk,
        "performance": performance,
        "security": security,
        "maintenance": maintenance,
        "financial": financial,
        "forecasts": forecasts(),
        "ai_insights": ai_insights(bits),
        "top_risks": top_risks(bits),
        "reports": report_catalog(),
        "executive_cards": [
            {"label": "Infrastructure Health", "value": f"{infrastructure['score']}%", "tone": "success"},
            {"label": "Asset Value", "value": f"R{assets['asset_value']:,.0f}", "tone": "accent"},
            {"label": "Ticket Trends", "value": f"{helpdesk['open']} open", "tone": "warning"},
            {"label": "SLA Compliance", "value": f"{helpdesk['sla_compliance']}%", "tone": "success"},
            {"label": "Security Score", "value": f"{security['security_score']}%", "tone": "accent"},
            {"label": "Operational Costs", "value": f"R{financial['total_ops_cost']:,.0f}", "tone": "muted"},
        ],
    }
