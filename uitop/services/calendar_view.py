"""IT Operations Calendar — aggregates events from UITOP modules."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from uitop.models.assets import Asset
from uitop.models.files import RepoFile
from uitop.models.helpdesk import Ticket
from uitop.models.maintenance import MaintenancePlan, MaintenanceWorkOrder
from uitop.models.security import SecurityIncident, SecurityPolicy
from uitop.services import backup_view as bv
from uitop.services import licenses_view as lic
from uitop.services.computers_view import relative_time


def utcnow():
    return datetime.now(timezone.utc)


EVENT_TYPES = {
    "maintenance": {"label": "Maintenance", "icon": "fa-wrench", "color": "#16a34a"},
    "backup": {"label": "Backup", "icon": "fa-hard-drive", "color": "#2563eb"},
    "update": {"label": "Software Update", "icon": "fa-download", "color": "#ea580c"},
    "license": {"label": "License", "icon": "fa-key", "color": "#9333ea"},
    "incident": {"label": "Incident", "icon": "fa-triangle-exclamation", "color": "#dc2626"},
    "change": {"label": "Change Request", "icon": "fa-code-branch", "color": "#ca8a04"},
    "meeting": {"label": "IT Meeting", "icon": "fa-users", "color": "#334155"},
    "warranty": {"label": "Warranty", "icon": "fa-certificate", "color": "#a16207"},
    "delivery": {"label": "Asset Delivery", "icon": "fa-truck", "color": "#0891b2"},
    "helpdesk": {"label": "Help Desk", "icon": "fa-life-ring", "color": "#0d9488"},
    "security": {"label": "Security", "icon": "fa-shield-halved", "color": "#be123c"},
    "monitoring": {"label": "Monitoring Window", "icon": "fa-heart-pulse", "color": "#4f46e5"},
    "document": {"label": "Document", "icon": "fa-file-lines", "color": "#64748b"},
}

SOURCE_FILTERS = (
    "maintenance",
    "backup",
    "license",
    "warranty",
    "helpdesk",
    "security",
    "monitoring",
    "update",
    "delivery",
    "change",
    "document",
)


def _as_utc(dt: datetime | date | None) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime(dt.year, dt.month, dt.day, 9, 0, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _event(
    *,
    eid: str,
    etype: str,
    title: str,
    start: datetime | date,
    url: str | None = None,
    end: datetime | None = None,
    all_day: bool = False,
    device: str | None = None,
    assignee: str | None = None,
    description: str | None = None,
    severity: str | None = None,
    source_module: str | None = None,
    meta: dict | None = None,
) -> dict:
    start_dt = _as_utc(start)
    end_dt = _as_utc(end) if end else None
    meta_type = EVENT_TYPES.get(etype, EVENT_TYPES["meeting"])
    return {
        "id": eid,
        "type": etype,
        "type_label": meta_type["label"],
        "icon": meta_type["icon"],
        "color": meta_type["color"],
        "title": title,
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
        "start_dt": start_dt,
        "all_day": all_day,
        "device": device or "—",
        "assignee": assignee or "—",
        "description": description or "",
        "severity": severity,
        "url": url,
        "source_module": source_module or etype,
        "meta": meta or {},
        "time_label": "All day" if all_day else (start_dt.strftime("%H:%M") if start_dt else "—"),
        "date_label": start_dt.strftime("%Y-%m-%d") if start_dt else "—",
        "when": relative_time(start_dt) if start_dt else "—",
    }


def _parse_backup_schedule(schedule: str) -> tuple[str, int, int]:
    """Return (cadence, hour, minute) — cadence: daily|weekday|weekly_sat."""
    text = (schedule or "").strip().lower()
    hour, minute = 2, 0
    for part in text.replace(".", ":").split():
        if ":" in part:
            try:
                h, m = part.split(":", 1)
                hour, minute = int(h), int(m[:2])
            except ValueError:
                pass
    if "weekday" in text:
        return "weekday", hour, minute
    if "sat" in text or "weekly" in text:
        return "weekly_sat", hour, minute
    return "daily", hour, minute


def _iter_backup_occurrences(job: dict, start: date, end: date) -> list[datetime]:
    cadence, hour, minute = _parse_backup_schedule(job.get("schedule") or "")
    out = []
    day = start
    while day <= end:
        use = False
        if cadence == "daily":
            use = True
        elif cadence == "weekday":
            use = day.weekday() < 5
        elif cadence == "weekly_sat":
            use = day.weekday() == 5
        if use:
            out.append(datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc))
        day += timedelta(days=1)
    return out


def collect_events(*, range_start: date | None = None, range_end: date | None = None) -> list[dict]:
    today = utcnow().date()
    range_start = range_start or (today - timedelta(days=7))
    range_end = range_end or (today + timedelta(days=45))
    events: list[dict] = []

    # Maintenance work orders
    for wo in MaintenanceWorkOrder.query.filter(MaintenanceWorkOrder.status != "cancelled").all():
        start = wo.scheduled_at or wo.due_at
        if not start:
            continue
        start = _as_utc(start)
        if not (range_start <= start.date() <= range_end):
            continue
        end = start + timedelta(hours=2)
        events.append(
            _event(
                eid=f"maint-{wo.id}",
                etype="maintenance",
                title=wo.title,
                start=start,
                end=end,
                device=wo.linked_label or "—",
                assignee=wo.technician.full_name if wo.technician else "Unassigned",
                description=wo.description,
                severity=wo.priority,
                url=f"/maintenance/{wo.id}",
                source_module="maintenance",
                meta={
                    "work_order": wo.work_order_number,
                    "status": wo.status,
                    "type": wo.maintenance_type,
                    "suppress_monitoring": True,
                },
            )
        )

    # Maintenance plans (next run)
    for plan in MaintenancePlan.query.filter_by(is_active=True).all():
        if not plan.next_run_at:
            continue
        start = _as_utc(plan.next_run_at)
        if not (range_start <= start.date() <= range_end):
            continue
        events.append(
            _event(
                eid=f"plan-{plan.id}",
                etype="maintenance",
                title=f"Plan: {plan.name}",
                start=start,
                description=plan.description,
                url="/maintenance/?view=plans",
                source_module="maintenance",
                meta={"frequency": plan.frequency},
            )
        )

    # Backup schedules → occurrences
    for job in bv.backup_jobs():
        for occ in _iter_backup_occurrences(job, range_start, range_end):
            events.append(
                _event(
                    eid=f"backup-{job['id']}-{occ.strftime('%Y%m%d%H%M')}",
                    etype="backup",
                    title=job["name"],
                    start=occ,
                    end=occ + timedelta(hours=1),
                    device=job.get("target"),
                    description=f"{job.get('type')} · {job.get('policy')} · {job.get('storage')}",
                    url=f"/backup/{job['id']}",
                    source_module="backup",
                    meta={"schedule": job.get("schedule"), "status": job.get("status")},
                )
            )

    # License expiry (all-day)
    for row in lic.licenses():
        try:
            exp = date.fromisoformat(row["expiry"])
        except (KeyError, ValueError):
            continue
        if not (range_start <= exp <= range_end):
            continue
        events.append(
            _event(
                eid=f"license-{row['id']}",
                etype="license",
                title=f"{row['product']} expires",
                start=exp,
                all_day=True,
                device=row.get("vendor"),
                assignee=row.get("owner"),
                description=f"Renew before {row['expiry']}. Seats {row.get('assigned')}/{row.get('purchased')}.",
                url=f"/licenses/{row['id']}",
                source_module="license",
                meta={"expiry": row["expiry"]},
            )
        )

    # Asset warranties
    for asset in Asset.query.filter(Asset.warranty_expires.isnot(None)).all():
        exp = asset.warranty_expires
        if not (range_start <= exp <= range_end):
            continue
        events.append(
            _event(
                eid=f"warranty-{asset.id}",
                etype="warranty",
                title=f"Warranty ends — {asset.name}",
                start=exp,
                all_day=True,
                device=asset.asset_tag,
                description=f"{asset.vendor.name if asset.vendor else 'Vendor'} warranty expiry.",
                url=f"/assets/{asset.id}",
                source_module="warranty",
                meta={"warranty_expires": exp.isoformat()},
            )
        )

    # Asset deliveries — purchase dates in window as delivery markers
    for asset in Asset.query.filter(Asset.purchase_date.isnot(None)).all():
        pd = asset.purchase_date
        if not (range_start <= pd <= range_end):
            continue
        if abs((pd - today).days) > 21 and asset.status not in ("in_store", "pending"):
            continue
        events.append(
            _event(
                eid=f"delivery-{asset.id}",
                etype="delivery",
                title=f"Asset delivery — {asset.name}",
                start=datetime(pd.year, pd.month, pd.day, 9, 0, tzinfo=timezone.utc),
                device=asset.asset_tag,
                description=f"PO {asset.po_number or '—'}",
                url=f"/assets/{asset.id}",
                source_module="delivery",
            )
        )

    # Help Desk SLA due
    for ticket in Ticket.query.filter(
        Ticket.status.in_(("open", "in_progress", "pending")),
        Ticket.sla_due_at.isnot(None),
    ).all():
        due = _as_utc(ticket.sla_due_at)
        if not due or not (range_start <= due.date() <= range_end):
            continue
        events.append(
            _event(
                eid=f"ticket-{ticket.id}",
                etype="helpdesk",
                title=ticket.subject,
                start=due,
                device=ticket.location or (ticket.asset.asset_tag if ticket.asset else None),
                assignee=ticket.assignee.full_name if ticket.assignee else "Unassigned",
                description=f"{ticket.ticket_number} · SLA due",
                severity=ticket.priority,
                url=f"/helpdesk/{ticket.id}",
                source_module="helpdesk",
                meta={"ticket_number": ticket.ticket_number},
            )
        )

    # Security incidents (open) as calendar markers on detected day + follow-ups
    for inc in SecurityIncident.query.filter(
        SecurityIncident.status.in_(("open", "investigating", "contained"))
    ).all():
        start = _as_utc(inc.detected_at)
        if not start or not (range_start <= start.date() <= range_end):
            continue
        events.append(
            _event(
                eid=f"secinc-{inc.id}",
                etype="incident" if inc.severity in ("critical", "high") else "security",
                title=inc.title,
                start=start,
                device=inc.hostname,
                assignee=inc.assignee.full_name if inc.assignee else "Unassigned",
                description=inc.description,
                severity=inc.severity,
                url="/security/?view=incidents",
                source_module="security",
                meta={"incident_number": inc.incident_number},
            )
        )

    # Security policy reviews (synthetic weekly Friday 10:00 if policies exist)
    if SecurityPolicy.query.count():
        day = range_start
        while day <= range_end:
            if day.weekday() == 4:  # Friday
                events.append(
                    _event(
                        eid=f"sec-policy-{day.isoformat()}",
                        etype="security",
                        title="Firewall / endpoint policy review",
                        start=datetime(day.year, day.month, day.day, 10, 0, tzinfo=timezone.utc),
                        end=datetime(day.year, day.month, day.day, 11, 0, tzinfo=timezone.utc),
                        description="Weekly security control review.",
                        url="/security/?view=policies",
                        source_module="security",
                    )
                )
            day += timedelta(days=1)

    # Document expiry
    for doc in RepoFile.query.filter(
        RepoFile.is_deleted.is_(False),
        RepoFile.kind == "document",
        RepoFile.expires_at.isnot(None),
    ).all():
        exp = _as_utc(doc.expires_at)
        if not exp or not (range_start <= exp.date() <= range_end):
            continue
        events.append(
            _event(
                eid=f"doc-{doc.id}",
                etype="document",
                title=f"Document expires — {doc.name}",
                start=exp.date(),
                all_day=True,
                description=doc.category,
                url=f"/documents/{doc.id}",
                source_module="document",
            )
        )

    # Demo change + patch windows (ops timeline richness)
    sat = today + timedelta(days=(5 - today.weekday()) % 7)
    if range_start <= sat <= range_end:
        events.append(
            _event(
                eid="change-firewall-upgrade",
                etype="change",
                title="Firewall upgrade (approved)",
                start=datetime(sat.year, sat.month, sat.day, 23, 0, tzinfo=timezone.utc),
                end=datetime(sat.year, sat.month, sat.day, 23, 0, tzinfo=timezone.utc) + timedelta(hours=2),
                device="Edge firewall",
                assignee="Network Team",
                description="Approved change window — monitoring suppressed.",
                url="/security/?view=overview",
                source_module="change",
                meta={"suppress_monitoring": True, "approved": True},
            )
        )
    sun = sat + timedelta(days=1)
    if range_start <= sun <= range_end:
        events.append(
            _event(
                eid="update-windows-sunday",
                etype="update",
                title="Windows Update — servers",
                start=datetime(sun.year, sun.month, sun.day, 2, 0, tzinfo=timezone.utc),
                end=datetime(sun.year, sun.month, sun.day, 4, 0, tzinfo=timezone.utc),
                device="Server farm",
                description="Staged OS patching. Monitoring muted during window.",
                url="/monitoring/?view=servers",
                source_module="update",
                meta={"suppress_monitoring": True},
            )
        )

    # Monitoring suppression companion for maintenance (same day evening)
    for ev in list(events):
        if ev["type"] == "maintenance" and ev.get("meta", {}).get("suppress_monitoring"):
            start = ev["start_dt"]
            events.append(
                _event(
                    eid=f"mon-suppress-{ev['id']}",
                    etype="monitoring",
                    title=f"Monitoring suppressed — {ev['device']}",
                    start=start,
                    end=start + timedelta(hours=2) if start else None,
                    device=ev["device"],
                    description="Alerts muted during maintenance window.",
                    url="/monitoring/?view=alerts",
                    source_module="monitoring",
                    meta={"linked_event": ev["id"]},
                )
            )

    events.sort(key=lambda e: e["start_dt"] or datetime.max.replace(tzinfo=timezone.utc))
    # Drop start_dt for JSON (keep iso strings)
    for e in events:
        e.pop("start_dt", None)
    return events


def calendar_kpis(events: list[dict] | None = None) -> dict:
    today = utcnow().date()
    month_end = today + timedelta(days=30)
    week_end = today + timedelta(days=7)
    events = events if events is not None else collect_events(range_start=today - timedelta(days=1), range_end=month_end)

    def _day(e):
        return date.fromisoformat(e["start"][:10]) if e.get("start") else None

    today_events = [e for e in events if _day(e) == today]
    return {
        "today": len(today_events),
        "maintenance": sum(1 for e in today_events if e["type"] == "maintenance"),
        "backups": sum(1 for e in today_events if e["type"] == "backup"),
        "expiring_licenses": sum(
            1 for e in events if e["type"] == "license" and _day(e) and today <= _day(e) <= month_end
        ),
        "critical_changes": sum(
            1
            for e in events
            if e["type"] in ("change", "incident")
            and e.get("severity") in ("critical", "high", None)
            and _day(e)
            and today <= _day(e) <= week_end
            and (e["type"] == "change" or e.get("severity") == "critical")
        ),
        "upcoming_warranties": sum(
            1 for e in events if e["type"] == "warranty" and _day(e) and today <= _day(e) <= week_end + timedelta(days=7)
        ),
    }


def ai_suggestions() -> list[dict]:
    return [
        {
            "title": "Shift evening backups later",
            "body": "Move backup from 18:00 toward 23:30 — network usage typically drops ~68% after hours.",
            "tone": "accent",
        },
        {
            "title": "Prefer Saturday for disruptive maintenance",
            "body": "Employee activity is lowest on Saturdays. Schedule server patching outside weekday peaks.",
            "tone": "warning",
        },
        {
            "title": "Conflict watch",
            "body": "Avoid overlapping full backups with approved change windows on the same host.",
            "tone": "danger",
        },
    ]


def build_module_payload(*, view: str = "month", year: int | None = None, month: int | None = None, day: str | None = None) -> dict:
    now = utcnow()
    year = year or now.year
    month = month or now.month
    # Wide collection window for month view
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    # Pad for week cells
    range_start = first - timedelta(days=7)
    range_end = last + timedelta(days=45)
    events = collect_events(range_start=range_start, range_end=range_end)
    kpis = calendar_kpis(events)

    # Month grid
    start_pad = (first.weekday() + 1) % 7  # Monday-first → Sunday-first optional; use Monday=0
    # ISO weekday Mon=0 … use Mon-start
    lead = first.weekday()  # Mon=0
    cells = []
    cursor = first - timedelta(days=lead)
    for _ in range(42):
        day_events = [e for e in events if e.get("start", "").startswith(cursor.isoformat())]
        cells.append(
            {
                "date": cursor.isoformat(),
                "day": cursor.day,
                "in_month": cursor.month == month,
                "is_today": cursor == now.date(),
                "events": day_events[:8],
                "count": len(day_events),
            }
        )
        cursor += timedelta(days=1)

    focus = now.date()
    if day:
        try:
            focus = date.fromisoformat(day)
        except ValueError:
            pass

    week_start = focus - timedelta(days=focus.weekday())
    week_days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_events = [e for e in events if e.get("start", "").startswith(d.isoformat())]
        week_days.append({"date": d.isoformat(), "label": d.strftime("%a %d"), "events": day_events, "is_today": d == now.date()})

    day_events = [e for e in events if e.get("start", "").startswith(focus.isoformat())]
    agenda = [e for e in events if e.get("start") and date.fromisoformat(e["start"][:10]) >= now.date()][:40]
    timeline = agenda[:25]

    return {
        "kpis": kpis,
        "events": events,
        "event_types": EVENT_TYPES,
        "filters": SOURCE_FILTERS,
        "view": view,
        "year": year,
        "month": month,
        "month_label": first.strftime("%B %Y"),
        "focus_day": focus.isoformat(),
        "month_cells": cells,
        "week_days": week_days,
        "day_events": day_events,
        "agenda": agenda,
        "timeline": timeline,
        "ai_suggestions": ai_suggestions(),
        "today_label": now.strftime("%A, %d %B %Y"),
    }


def get_event_detail(event_id: str) -> dict | None:
    # Search a generous window
    today = utcnow().date()
    events = collect_events(range_start=today - timedelta(days=30), range_end=today + timedelta(days=60))
    for e in events:
        if e["id"] == event_id:
            return e
    return None
