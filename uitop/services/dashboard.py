"""Aggregate live metrics for the operations dashboard."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func

from uitop.extensions import db
from uitop.models.agent_telemetry import AgentAlert, PerformanceSample
from uitop.models.assets import Asset, AssetRequest
from uitop.models.audit import AuditLog
from uitop.models.department import Department
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.services.computers_view import derive_presence, relative_time, serialize_computer, utcnow
from uitop.services import helpdesk as hd_svc


def _online_computers() -> tuple[int, int]:
    rows = Computer.query.all()
    online = 0
    for c in rows:
        status, _ = derive_presence(c)
        if status == "Online":
            online += 1
    return online, len(rows)


def _online_servers() -> tuple[int, int]:
    rows = Server.query.all()
    online = 0
    for s in rows:
        status, _ = derive_presence(type("P", (), {"status": s.status, "agent_id": s.agent_id, "last_seen_at": s.last_seen_at})())
        if status == "Online":
            online += 1
    return online, len(rows)


def build_dashboard() -> dict:
    devices_online, devices_total = _online_computers()
    servers_online, servers_total = _online_servers()
    network_total = NetworkDevice.query.count()
    network_online = NetworkDevice.query.filter(NetworkDevice.status.in_(["online", "Online"])).count()
    printers_total = Printer.query.count()
    assets_total = Asset.query.count()
    assets_assigned = Asset.query.filter(Asset.status.in_(["assigned", "in_use"])).count()
    assets_store = Asset.query.filter_by(status="in_store").count()
    pending_requests = AssetRequest.query.filter_by(status="pending").count()
    critical_alerts = AgentAlert.query.filter(
        AgentAlert.status == "open",
        AgentAlert.severity.in_(["critical", "error", "warning"]),
    ).count()
    open_alerts = AgentAlert.query.filter_by(status="open").count()
    ticket_kpis = hd_svc.ticket_kpis()
    tickets_open = ticket_kpis["open"]
    tickets_breached = ticket_kpis["sla_breached"]

    # Hot devices by latest CPU sample
    hot = []
    for computer in Computer.query.order_by(Computer.hostname).limit(40):
        sample = (
            PerformanceSample.query.filter_by(computer_id=computer.id)
            .order_by(PerformanceSample.collected_at.desc())
            .first()
        )
        row = serialize_computer(computer, sample)
        pressure = max(row["cpu"], row["ram"], row["disk"])
        hot.append({**row, "pressure": pressure})
    hot.sort(key=lambda r: r["pressure"], reverse=True)
    hot = hot[:5]

    # Activity from audit log
    audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(12).all()
    activity = []
    for a in audits:
        activity.append(
            {
                "title": a.action.replace(".", " · "),
                "meta": f"{a.resource_type or 'system'}{(' #' + str(a.resource_id)) if a.resource_id else ''}",
                "time": relative_time(a.created_at),
                "icon": _action_icon(a.action),
                "tone": _action_tone(a.action),
            }
        )

    # Dept asset share
    dept_rows = (
        db.session.query(Department.name, func.count(Asset.id))
        .outerjoin(Asset, Asset.department_id == Department.id)
        .group_by(Department.id)
        .all()
    )
    # Also count assets with no department as Unassigned
    no_dept = Asset.query.filter(Asset.department_id.is_(None)).count()
    dept_labels = [r[0] for r in dept_rows]
    dept_values = [int(r[1]) for r in dept_rows]
    if no_dept:
        dept_labels.append("Unassigned")
        dept_values.append(no_dept)

    # Ticket status mix for dashboard donut
    mix_labels, mix_values = hd_svc.status_mix()

    # Infra series from recent performance samples (avg cpu/mem)
    since = utcnow() - timedelta(hours=24)
    samples = (
        PerformanceSample.query.filter(PerformanceSample.collected_at >= since)
        .order_by(PerformanceSample.collected_at.asc())
        .limit(200)
        .all()
    )
    infra_labels = []
    infra_cpu = []
    infra_mem = []
    if samples:
        # bucket into ~12 points
        step = max(1, len(samples) // 12)
        buckets = samples[::step][:12]
        for s in buckets:
            infra_labels.append(s.collected_at.strftime("%H:%M") if s.collected_at else "")
            infra_cpu.append(round(s.cpu_percent or 0, 1))
            infra_mem.append(round(s.memory_percent or 0, 1))
    else:
        infra_labels = ["now"]
        infra_cpu = [0]
        infra_mem = [0]

    # Alert velocity last 7 days (counts per day)
    alert_labels = []
    alert_raised = []
    alert_resolved = []
    for i in range(6, -1, -1):
        day = (utcnow() - timedelta(days=i)).date()
        alert_labels.append(day.strftime("%a"))
        start = day.isoformat()
        # SQLite-friendly filter via python
        raised = 0
        resolved = 0
        day_alerts = AgentAlert.query.filter(
            AgentAlert.occurred_at >= utcnow() - timedelta(days=7)
        ).all()
        for al in day_alerts:
            if al.occurred_at and al.occurred_at.date() == day:
                raised += 1
                if al.status == "resolved" or al.resolved_at:
                    resolved += 1
        alert_raised.append(raised)
        alert_resolved.append(resolved)

    health_score = 100
    if devices_total and devices_online / max(devices_total, 1) < 0.8:
        health_score -= 15
    if critical_alerts:
        health_score -= min(30, critical_alerts * 5)
    if servers_total and servers_online < servers_total:
        health_score -= 5
    if tickets_breached:
        health_score -= min(15, tickets_breached * 3)
    health_score = max(55, health_score)

    return {
        "kpis": {
            "devices_online": devices_online,
            "devices_total": devices_total,
            "servers_online": servers_online,
            "servers_total": servers_total,
            "network_total": network_total,
            "printers_total": printers_total,
            "assets_total": assets_total,
            "assets_assigned": assets_assigned,
            "assets_store": assets_store,
            "pending_requests": pending_requests,
            "critical_alerts": critical_alerts,
            "open_alerts": open_alerts,
            "tickets_open": tickets_open,
            "tickets_breached": tickets_breached,
            "tickets_resolved_today": ticket_kpis["resolved_today"],
            "health_score": health_score,
        },
        "hot_devices": hot,
        "activity": activity,
        "charts": {
            "mix_labels": mix_labels,
            "mix_values": mix_values,
            "dept_labels": dept_labels or ["None"],
            "dept_values": dept_values or [0],
            "infra_labels": infra_labels,
            "infra_cpu": infra_cpu,
            "infra_mem": infra_mem,
            "alert_labels": alert_labels,
            "alert_raised": alert_raised,
            "alert_resolved": alert_resolved,
        },
    }


def _action_icon(action: str) -> str:
    if action.startswith("helpdesk."):
        return "fa-ticket"
    if action.startswith("agents."):
        return "fa-robot"
    if action.startswith("assets."):
        return "fa-box"
    if action.startswith("auth."):
        return "fa-user-shield"
    if "alert" in action:
        return "fa-bell"
    return "fa-circle-nodes"


def _action_tone(action: str) -> str:
    if "alert" in action or "fail" in action:
        return "danger"
    if "warning" in action or "request" in action:
        return "warning"
    return ""
