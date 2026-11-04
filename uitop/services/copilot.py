"""IT Copilot service — natural-language queries over the UITOP database.

Flow:
1. classify_intent() — detect what the user is asking about.
2. gather_context()  — run targeted DB queries based on intents + RBAC.
3. ask_copilot()     — send system prompt + DB context + history to OpenRouter.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone

from flask import session

from uitop.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _user_permissions() -> list[str]:
    return session.get("permissions") or []


def _has(*codes: str) -> bool:
    perms = _user_permissions()
    user = session.get("user") or {}
    if user.get("is_super_admin"):
        return True
    if not perms:
        # Session may not have granular perms in demo — allow reads
        return True
    return any(c in perms for c in codes)


# ---------------------------------------------------------------------------
# Context gatherers
# ---------------------------------------------------------------------------

def _ctx_dashboard() -> dict:
    from uitop.models import Computer, Printer, Server, Ticket

    try:
        computers_online = Computer.query.filter_by(status="online").count()
        computers_offline = Computer.query.filter_by(status="offline").count()
        computers_total = Computer.query.count()
        servers_total = Server.query.count()
        printers_offline = Printer.query.filter_by(status="offline").count()
        printers_total = Printer.query.count()
        open_tickets = Ticket.query.filter(Ticket.status.in_(["open", "in_progress", "pending"])).count()
        high_tickets = Ticket.query.filter(
            Ticket.status.in_(["open", "in_progress"]),
            Ticket.priority.in_(["high", "critical"]),
        ).count()
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today = Ticket.query.filter(
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at >= today,
        ).count()

        backup = {}
        try:
            from uitop.services import backup_view

            backup = backup_view.kpis()
        except Exception:
            pass

        online_pct = round((computers_online / computers_total) * 100) if computers_total else 0
        return {
            "computers_online": computers_online,
            "computers_offline": computers_offline,
            "computers_total": computers_total,
            "servers_total": servers_total,
            "printers_offline": printers_offline,
            "printers_total": printers_total,
            "open_tickets": open_tickets,
            "high_priority_tickets": high_tickets,
            "tickets_resolved_today": resolved_today,
            "device_online_pct": online_pct,
            "backup_summary": backup,
        }
    except Exception:
        return {}


def _ctx_computers(query_text: str) -> dict:
    from uitop.models import Computer, Department

    try:
        q = Computer.query
        tl = query_text.lower()

        # Department filter e.g. "in HR" / "in Finance"
        dept_match = re.search(r"\bin\s+([a-zA-Z][\w\s-]{1,40})", tl)
        if dept_match:
            dept_name = dept_match.group(1).strip()
            # strip trailing words that are not department names
            for stop in (" that", " with", " which", " today", " still", " under"):
                if stop in dept_name:
                    dept_name = dept_name.split(stop)[0].strip()
            dept = Department.query.filter(Department.name.ilike(f"%{dept_name}%")).first()
            if dept:
                q = q.filter_by(department_id=dept.id)

        for kw in ("dell", "hp", "lenovo", "apple", "acer", "asus", "microsoft"):
            if kw in tl:
                q = q.filter(Computer.manufacturer.ilike(f"%{kw}%"))
                break
        if "windows 11" in tl:
            q = q.filter(db.or_(Computer.os_name.ilike("%windows 11%"), Computer.os_version.ilike("%11%")))
        if "windows 10" in tl:
            q = q.filter(db.or_(Computer.os_name.ilike("%windows 10%"), Computer.os_version.ilike("%10%")))
        if "laptop" in tl:
            q = q.filter(db.or_(Computer.model.ilike("%laptop%"), Computer.hostname.ilike("%laptop%")))
        if "offline" in tl:
            q = q.filter_by(status="offline")
        elif "online" in tl:
            q = q.filter_by(status="online")
        if "ssd" in tl:
            q = q.filter(Computer.inventory_payload.isnot(None))

        # Hostname / asset tag lookup
        tag_match = re.search(r"\b([A-Z]{1,6}[-_]?\d{2,6})\b", query_text, re.I)
        if tag_match:
            token = tag_match.group(1)
            q = Computer.query.filter(
                db.or_(
                    Computer.hostname.ilike(f"%{token}%"),
                    Computer.asset_tag.ilike(f"%{token}%"),
                    Computer.serial_number.ilike(f"%{token}%"),
                )
            )

        if "haven't checked in" in tl or "not checked in" in tl or "last seen" in tl:
            today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            q = q.filter(db.or_(Computer.last_seen_at.is_(None), Computer.last_seen_at < today))

        computers = q.order_by(Computer.hostname).limit(25).all()
        rows = []
        for c in computers:
            rows.append({
                "hostname": c.hostname,
                "asset_tag": c.asset_tag,
                "manufacturer": c.manufacturer,
                "model": c.model,
                "os": c.os_name,
                "status": c.status,
                "ram_gb": c.ram_gb,
                "disk_gb": c.disk_gb,
                "department": c.department.name if c.department else None,
                "ip": c.ip_address,
                "last_seen": c.last_seen_at.isoformat() if c.last_seen_at else None,
            })
        return {"computers": rows, "total_matched": len(rows)}
    except Exception:
        return {}


def _ctx_tickets(query_text: str) -> dict:
    from uitop.models import Ticket, User

    try:
        tl = query_text.lower()
        q = Ticket.query
        if "open" in tl:
            q = q.filter(Ticket.status.in_(["open", "in_progress", "pending"]))
        if "overdue" in tl:
            now = utcnow()
            q = q.filter(
                Ticket.status.in_(["open", "in_progress", "pending"]),
                Ticket.sla_due_at.isnot(None),
                Ticket.sla_due_at < now,
            )
        if "high" in tl or "critical" in tl:
            q = q.filter(Ticket.priority.in_(["high", "critical"]))
        if "today" in tl or "incident" in tl:
            today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            if "today" in tl:
                q = q.filter(Ticket.created_at >= today)
            if "incident" in tl:
                q = q.filter_by(ticket_type="incident")

        tickets = q.order_by(Ticket.created_at.desc()).limit(15).all()
        rows = []
        for t in tickets:
            rows.append({
                "number": t.ticket_number,
                "subject": t.subject,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "type": t.ticket_type,
                "assignee": t.assignee.full_name if t.assignee else "Unassigned",
                "department": t.department.name if t.department else None,
                "created": t.created_at.isoformat() if t.created_at else None,
            })

        from sqlalchemy import func

        top = (
            db.session.query(Ticket.assignee_user_id, func.count(Ticket.id).label("cnt"))
            .filter(
                Ticket.status.in_(["open", "in_progress", "pending"]),
                Ticket.assignee_user_id.isnot(None),
            )
            .group_by(Ticket.assignee_user_id)
            .order_by(func.count(Ticket.id).desc())
            .first()
        )
        top_tech = None
        if top:
            u = db.session.get(User, top[0])
            top_tech = {"name": u.full_name if u else str(top[0]), "open_tickets": top[1]}

        # Average resolution time (hours) for resolved tickets this month
        month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        resolved = Ticket.query.filter(
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at >= month_start,
            Ticket.created_at.isnot(None),
        ).limit(200).all()
        avg_hours = None
        if resolved:
            deltas = [
                (t.resolved_at - t.created_at).total_seconds() / 3600
                for t in resolved
                if t.resolved_at and t.created_at
            ]
            if deltas:
                avg_hours = round(sum(deltas) / len(deltas), 1)

        # Category breakdown this month
        cat_rows = (
            db.session.query(Ticket.category, func.count(Ticket.id))
            .filter(Ticket.created_at >= month_start)
            .group_by(Ticket.category)
            .order_by(func.count(Ticket.id).desc())
            .limit(8)
            .all()
        )
        by_category = [{"category": c or "other", "count": n} for c, n in cat_rows]

        return {
            "tickets": rows,
            "top_technician": top_tech,
            "avg_resolution_hours_this_month": avg_hours,
            "tickets_by_category_this_month": by_category,
        }
    except Exception:
        return {}


def _ctx_assets(query_text: str) -> dict:
    from uitop.models import Asset, AssetAssignment, Department

    try:
        tl = query_text.lower()
        q = Asset.query

        tag_match = re.search(r"\b([A-Z]{1,6}[-_]?\d{2,6})\b", query_text, re.I)
        if tag_match:
            token = tag_match.group(1)
            q = Asset.query.filter(
                db.or_(
                    Asset.asset_tag.ilike(f"%{token}%"),
                    Asset.name.ilike(f"%{token}%"),
                    Asset.serial_number.ilike(f"%{token}%"),
                )
            )
        else:
            for kw in ("laptop", "printer", "monitor", "keyboard", "server", "phone", "desktop"):
                if kw in tl:
                    q = q.filter(db.or_(Asset.name.ilike(f"%{kw}%"), Asset.asset_tag.ilike(f"%{kw}%")))
                    break
            if "warranty" in tl:
                today = utcnow().date()
                q = q.filter(Asset.warranty_expires.isnot(None), Asset.warranty_expires >= today)
            dept_match = re.search(r"\bin\s+([a-zA-Z][\w\s-]{1,40})", tl)
            if dept_match:
                dept_name = dept_match.group(1).strip()
                dept = Department.query.filter(Department.name.ilike(f"%{dept_name}%")).first()
                if dept:
                    q = q.filter_by(department_id=dept.id)

        assets = q.limit(20).all()
        rows = []
        for a in assets:
            assignment = AssetAssignment.query.filter_by(asset_id=a.id, returned_at=None).first()
            assigned = None
            if assignment and assignment.user:
                assigned = assignment.user.full_name
            elif a.custodian:
                assigned = a.custodian.full_name
            rows.append({
                "tag": a.asset_tag,
                "name": a.name,
                "status": a.status,
                "assigned_to": assigned,
                "department": a.department.name if a.department else None,
                "location": a.location,
                "warranty_expires": a.warranty_expires.isoformat() if a.warranty_expires else None,
            })

        # Expiring warranties (next 90 days)
        soon = utcnow().date() + timedelta(days=90)
        expiring = Asset.query.filter(
            Asset.warranty_expires.isnot(None),
            Asset.warranty_expires <= soon,
            Asset.warranty_expires >= utcnow().date(),
        ).limit(10).all()
        expiring_rows = [
            {"tag": a.asset_tag, "name": a.name, "warranty_expires": a.warranty_expires.isoformat()}
            for a in expiring
        ]
        return {"assets": rows, "warranties_expiring_90_days": expiring_rows}
    except Exception:
        return {}


def _ctx_printers(query_text: str) -> dict:
    from uitop.models import Printer

    try:
        tl = query_text.lower()
        q = Printer.query
        if "offline" in tl:
            q = q.filter_by(status="offline")
        if "hp" in tl:
            q = q.filter(db.or_(Printer.model.ilike("%hp%"), Printer.name.ilike("%hp%")))
        printers = q.limit(20).all()
        rows = []
        for p in printers:
            rows.append({
                "name": p.name,
                "ip": p.ip_address,
                "status": p.status,
                "model": p.model,
                "location": p.location,
            })
        return {"printers": rows, "total": len(rows)}
    except Exception:
        return {}


def _ctx_servers(query_text: str) -> dict:
    from uitop.models import Server

    try:
        tl = query_text.lower()
        q = Server.query
        if "offline" in tl:
            q = q.filter_by(status="offline")
        servers = q.limit(20).all()
        rows = []
        for s in servers:
            rows.append({
                "hostname": s.hostname,
                "ip": s.ip_address,
                "status": s.status,
                "os": getattr(s, "os_name", None),
                "role": getattr(s, "role", None),
                "last_seen": s.last_seen_at.isoformat() if getattr(s, "last_seen_at", None) else None,
            })
        return {"servers": rows, "total": len(rows)}
    except Exception:
        return {}


def _ctx_backup() -> dict:
    try:
        from uitop.services import backup_view

        jobs = backup_view.backup_jobs()
        kpis = backup_view.kpis()
        failed = [j for j in jobs if str(j.get("status", "")).lower() in ("failed", "error")]
        return {
            "kpis": kpis,
            "failed_jobs": failed[:10],
            "recent_jobs": jobs[:10],
        }
    except Exception:
        return {}


def _ctx_monitoring() -> dict:
    from uitop.models import AgentAlert, Computer, Server

    try:
        alerts = []
        try:
            rows = AgentAlert.query.order_by(AgentAlert.created_at.desc()).limit(15).all()
            for a in rows:
                severity = getattr(a, "severity", None) or getattr(a, "level", "info")
                alerts.append({
                    "title": getattr(a, "title", None) or getattr(a, "message", "Alert"),
                    "severity": severity,
                    "status": getattr(a, "status", None),
                    "at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
                })
        except Exception:
            pass

        offline_computers = Computer.query.filter_by(status="offline").limit(15).all()
        offline_servers = Server.query.filter_by(status="offline").limit(10).all()
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stale = Computer.query.filter(
            db.or_(Computer.last_seen_at.is_(None), Computer.last_seen_at < today)
        ).limit(15).all()

        return {
            "alerts": alerts,
            "offline_computers": [{"hostname": c.hostname, "last_seen": c.last_seen_at.isoformat() if c.last_seen_at else None} for c in offline_computers],
            "offline_servers": [{"hostname": s.hostname} for s in offline_servers],
            "not_checked_in_today": [{"hostname": c.hostname, "last_seen": c.last_seen_at.isoformat() if c.last_seen_at else None} for c in stale],
        }
    except Exception:
        return {}


def _ctx_security() -> dict:
    from uitop.models import SecurityIncident, SecurityThreat

    try:
        incidents = SecurityIncident.query.filter(
            SecurityIncident.status != "closed"
        ).order_by(SecurityIncident.created_at.desc()).limit(10).all()
        threats = SecurityThreat.query.filter(
            SecurityThreat.status != "resolved"
        ).limit(10).all()
        return {
            "open_incidents": [
                {
                    "title": getattr(i, "title", "Incident"),
                    "severity": getattr(i, "severity", None),
                    "status": i.status,
                }
                for i in incidents
            ],
            "active_threats": [
                {
                    "name": getattr(t, "threat_name", None) or getattr(t, "name", "Threat"),
                    "severity": getattr(t, "severity", None),
                }
                for t in threats
            ],
        }
    except Exception:
        return {}


def _ctx_audit() -> dict:
    from uitop.models import AuditLog

    try:
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        logs = AuditLog.query.filter(AuditLog.created_at >= today).order_by(
            AuditLog.created_at.desc()
        ).limit(20).all()
        rows = []
        for l in logs:
            rows.append({
                "action": getattr(l, "action", None),
                "resource": getattr(l, "resource_type", None) or getattr(l, "entity_type", None),
                "user_id": getattr(l, "user_id", None),
                "at": l.created_at.isoformat() if l.created_at else None,
            })
        return {"audit_entries_today": rows}
    except Exception:
        return {}


def _ctx_files(query_text: str) -> dict:
    from uitop.models import RepoFile

    try:
        tl = query_text.lower()
        q = RepoFile.query
        for kw in ("printer", "server", "network", "diagram", "guide", "manual", "vpn", "backup"):
            if kw in tl:
                q = q.filter(
                    db.or_(
                        RepoFile.name.ilike(f"%{kw}%"),
                        getattr(RepoFile, "title", RepoFile.name).ilike(f"%{kw}%") if hasattr(RepoFile, "title") else RepoFile.name.ilike(f"%{kw}%"),
                    )
                )
                break
        files = q.order_by(RepoFile.updated_at.desc() if hasattr(RepoFile, "updated_at") else RepoFile.id.desc()).limit(15).all()
        rows = []
        for f in files:
            rows.append({
                "name": getattr(f, "name", None) or getattr(f, "title", "File"),
                "path": getattr(f, "path", None) or getattr(f, "storage_path", None),
                "category": getattr(f, "category", None),
                "id": f.id,
            })
        return {"files": rows}
    except Exception:
        return {}


def _ctx_licenses() -> dict:
    try:
        # Soft import — licenses module may use view helpers
        from routes import licenses as licenses_routes  # noqa: F401
    except Exception:
        pass
    try:
        # Try common model names
        from uitop import models as m

        License = getattr(m, "License", None) or getattr(m, "SoftwareLicense", None)
        if License is None:
            return {"note": "License inventory module is available in the UI; structured license rows were not found in models."}
        rows = License.query.limit(20).all()
        out = []
        for lic in rows:
            out.append({
                "name": getattr(lic, "name", None) or getattr(lic, "product_name", "License"),
                "seats": getattr(lic, "seats", None) or getattr(lic, "quantity", None),
                "used": getattr(lic, "used", None) or getattr(lic, "assigned", None),
                "expires": str(getattr(lic, "expires_at", None) or getattr(lic, "expiry_date", None) or ""),
                "status": getattr(lic, "status", None),
            })
        return {"licenses": out}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Intent classifier
# ---------------------------------------------------------------------------

_INTENTS = {
    "dashboard": [
        "how is it", "it health", "overview", "status today", "executive summary",
        "summary today", "daily briefing", "how is the it", "department doing",
        "give me today's", "it department",
    ],
    "computers": [
        "computer", "laptop", "workstation", "pc", "windows", "linux", "mac",
        "hostname", "last seen", "offline device", "disk space", "cpu", "ram",
        "dell", "hp-", "ssd", "checked in",
    ],
    "tickets": [
        "ticket", "helpdesk", "incident", "service request", "support",
        "technician", "overdue", "resolution time", "open ticket", "assign",
    ],
    "assets": [
        "asset", "warranty", "assigned to", "where is", "office", "finance department",
        "replacement", "custodian",
    ],
    "printers": ["printer", "print", "offline printer", "prn-"],
    "servers": ["server", "high cpu", "srv-"],
    "backup": [
        "backup", "restore", "failed backup", "hasn't backed up", "storage do backups",
        "recovery",
    ],
    "security": [
        "security", "threat", "vulnerability", "malware", "antivirus", "compliance",
    ],
    "audit": [
        "who deleted", "who restored", "admin actions", "audit", "who changed", "access log",
    ],
    "software": [
        "software", "microsoft office", "adobe", "license", "update", "patch", "expired license",
    ],
    "files": [
        "file", "document", "guide", "diagram", "manual", "documentation", "knowledge",
        "how do i", "how was", "article",
    ],
    "monitoring": [
        "monitoring", "alert", "cpu high", "memory", "low disk", "server down",
        "offline server", "critical alert", "checked in today",
    ],
    "maintenance": ["maintenance", "work order", "schedule", "repair"],
    "report": ["weekly it report", "monthly it report", "generate the", "export as pdf", "report"],
    "troubleshoot": ["why can't", "why cant", "not working", "troubleshoot", "event id", "error"],
}


def classify_intent(text: str) -> list[str]:
    tl = text.lower()
    found = []
    for intent, keywords in _INTENTS.items():
        if any(kw in tl for kw in keywords):
            found.append(intent)
    return found or ["general"]


def gather_context(query_text: str, intents: list[str]) -> dict:
    ctx: dict = {}

    if "dashboard" in intents or "report" in intents or "general" in intents:
        if _has("dashboard:read", "monitoring:read"):
            ctx["dashboard"] = _ctx_dashboard()

    if "computers" in intents or "troubleshoot" in intents:
        if _has("computers:read"):
            ctx["computers"] = _ctx_computers(query_text)

    if "tickets" in intents or "report" in intents:
        if _has("helpdesk:read"):
            ctx["helpdesk"] = _ctx_tickets(query_text)

    if "assets" in intents:
        if _has("assets:read"):
            ctx["assets"] = _ctx_assets(query_text)

    if "printers" in intents or "troubleshoot" in intents:
        if _has("printers:read"):
            ctx["printers"] = _ctx_printers(query_text)

    if "servers" in intents or "monitoring" in intents:
        if _has("servers:read"):
            ctx["servers"] = _ctx_servers(query_text)

    if "backup" in intents or "report" in intents:
        if _has("backup:read"):
            ctx["backup"] = _ctx_backup()

    if "security" in intents:
        if _has("security:read"):
            ctx["security"] = _ctx_security()

    if "audit" in intents:
        if _has("audit:read"):
            ctx["audit"] = _ctx_audit()

    if "monitoring" in intents or "troubleshoot" in intents:
        if _has("monitoring:read", "computers:read"):
            ctx["monitoring"] = _ctx_monitoring()

    if "files" in intents:
        if _has("files:read"):
            ctx["files"] = _ctx_files(query_text)

    if "software" in intents:
        if _has("licenses:read", "software:read"):
            ctx["licenses"] = _ctx_licenses()

    # Recommendations always when dashboard/report
    if "dashboard" in intents or "report" in intents:
        recs = []
        dash = ctx.get("dashboard") or {}
        if dash.get("high_priority_tickets"):
            recs.append(f"{dash['high_priority_tickets']} high/critical tickets need attention.")
        if dash.get("printers_offline"):
            recs.append(f"{dash['printers_offline']} printers are offline.")
        if dash.get("computers_offline"):
            recs.append(f"{dash['computers_offline']} computers are offline.")
        backup = dash.get("backup_summary") or {}
        if backup.get("failed"):
            recs.append(f"{backup['failed']} backup jobs failed recently.")
        assets = ctx.get("assets") or {}
        if assets.get("warranties_expiring_90_days"):
            n = len(assets["warranties_expiring_90_days"])
            recs.append(f"{n} device warranties expire within 90 days.")
        if recs:
            ctx["recommendations"] = recs

    return ctx


# ---------------------------------------------------------------------------
# OpenRouter / OpenAI call
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the IT Copilot for Umzinyathi Municipality's IT Operations Platform (UITOP).
You are an experienced municipal IT technician embedded in the platform — not a generic chatbot.

You help with: dashboard intelligence, assets, backups, helpdesk, knowledge/files, monitoring,
software/licenses, reports, analytics, audit, natural-language search, troubleshooting, and executive summaries.

Rules:
- Answer concisely and professionally. Prefer clear bullet points.
- Base answers ONLY on the LIVE DATABASE CONTEXT when numbers or inventory are involved.
- Never invent device counts, hostnames, ticket numbers, or storage figures.
- If context is empty for a topic, say data is unavailable or the user may lack permission.
- Suggest next actions with UITOP paths when helpful (e.g. /helpdesk, /computers, /backup).
- For Event ID / error explanations, give: meaning, criticality, causes, fixes.
- For executive summaries, use a compact KPI-style layout.
- Decline unrelated or unauthorized actions (e.g. delete all users).
- Keep answers focused on IT operations.
"""


def ask_copilot(question: str, history: list[dict], context: dict) -> str:
    """Call OpenRouter (preferred) or OpenAI with context and history."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-...") or "<OPENROUTER" in api_key:
        return _fallback_response(question, context)

    try:
        import openai

        use_openrouter = api_key.startswith("sk-or-") or bool(os.getenv("OPENROUTER_API_KEY"))
        if use_openrouter:
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                    "X-OpenRouter-Title": os.getenv("OPENROUTER_SITE_NAME", "UITOP IT Copilot"),
                },
            )
            model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        else:
            client = openai.OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        context_block = (
            "\n\n[LIVE DATABASE CONTEXT]\n"
            + json.dumps(context, indent=2, default=str)
            + "\n[END CONTEXT]\n"
            if context
            else "\n\n[LIVE DATABASE CONTEXT]\n{}\n[END CONTEXT]\n"
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_block}]
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=800,
            temperature=0.25,
        )
        content = response.choices[0].message.content
        return (content or "").strip() or "I received an empty response. Please try again."
    except Exception as e:
        return f"I encountered an error reaching the AI service: {e}. Check OPENROUTER_API_KEY in .env."


def _fallback_response(question: str, context: dict) -> str:
    if not context:
        return (
            "The IT Copilot is not fully configured yet. "
            "Add OPENROUTER_API_KEY to your .env file."
        )
    parts = ["Here is what I found in the system:\n"]
    if "dashboard" in context:
        d = context["dashboard"]
        parts.append(
            f"- **Computers online:** {d.get('computers_online', 'N/A')} / {d.get('computers_total', 'N/A')}\n"
            f"- **Open tickets:** {d.get('open_tickets', 'N/A')} "
            f"({d.get('high_priority_tickets', 0)} high/critical)\n"
            f"- **Printers offline:** {d.get('printers_offline', 'N/A')}\n"
        )
        if d.get("backup_summary"):
            b = d["backup_summary"]
            parts.append(f"- **Backup failures:** {b.get('failed', 'N/A')}\n")
    if context.get("recommendations"):
        parts.append("\n**Recommendations:**\n")
        for r in context["recommendations"]:
            parts.append(f"- {r}\n")
    if "helpdesk" in context:
        tickets = context["helpdesk"].get("tickets", [])
        if tickets:
            parts.append(f"\n**Recent tickets ({len(tickets)}):**\n")
            for t in tickets[:5]:
                parts.append(f"- [{t['number']}] {t['subject']} — {t['status']} ({t['priority']})\n")
    if "computers" in context:
        computers = context["computers"].get("computers", [])
        if computers:
            parts.append(f"\n**Computers found ({len(computers)}):**\n")
            for c in computers[:5]:
                parts.append(f"- {c['hostname']} — {c.get('manufacturer') or ''} {c.get('model') or ''} ({c['status']})\n")
    if "backup" in context:
        failed = context["backup"].get("failed_jobs") or []
        if failed:
            parts.append(f"\n**Failed backups ({len(failed)}):**\n")
            for j in failed[:5]:
                parts.append(f"- {j.get('name')} — {j.get('error') or j.get('status')}\n")
    return "".join(parts) if len(parts) > 1 else "I don't have enough context. Try a more specific IT operations question."
