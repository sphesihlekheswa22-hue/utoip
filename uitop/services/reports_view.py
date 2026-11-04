"""Reports — official reporting center (templates, schedules, exports, history).

Analysis = interactive insights. Reports = formal documents and exports.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from uitop.services import analysis_view as an
from uitop.services import assets as asset_svc
from uitop.services import helpdesk as hd_svc
from uitop.services import licenses_view as lic
from uitop.services import maintenance as mt_svc
from uitop.services import security_view as sec
from uitop.services import vendors_view as ven


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


REPORT_TYPES = [
    {
        "id": "executive",
        "name": "Executive Summary",
        "category": "Executive",
        "desc": "Health, security, tickets, costs, and top risks for management.",
        "formats": ["PDF", "Excel", "Word"],
        "icon": "fa-briefcase",
    },
    {
        "id": "infrastructure",
        "name": "Infrastructure Health",
        "category": "Infrastructure",
        "desc": "Device health distribution and availability by type.",
        "formats": ["PDF", "Excel", "CSV"],
        "icon": "fa-server",
    },
    {
        "id": "assets",
        "name": "Asset Inventory",
        "category": "Assets",
        "desc": "Full asset register with age, status, and replacement flags.",
        "formats": ["Excel", "CSV", "PDF"],
        "icon": "fa-boxes-stacked",
    },
    {
        "id": "helpdesk",
        "name": "Help Desk Performance",
        "category": "Help Desk",
        "desc": "Tickets created/closed, resolution times, SLA, technician load.",
        "formats": ["PDF", "Excel", "CSV"],
        "icon": "fa-headset",
    },
    {
        "id": "maintenance",
        "name": "Maintenance Summary",
        "category": "Maintenance",
        "desc": "Work orders, costs, overdue jobs, and technician performance.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-wrench",
    },
    {
        "id": "monitoring",
        "name": "Monitoring Report",
        "category": "Monitoring",
        "desc": "CPU/memory averages, uptime, critical alerts, and downtime.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-chart-line",
    },
    {
        "id": "security",
        "name": "Security Report",
        "category": "Security",
        "desc": "Security score, compliance, incidents, and devices at risk.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-shield-halved",
    },
    {
        "id": "software",
        "name": "Software Inventory",
        "category": "Software",
        "desc": "Installed titles, versions, and deployment footprint.",
        "formats": ["Excel", "CSV"],
        "icon": "fa-cube",
    },
    {
        "id": "licenses",
        "name": "License Compliance",
        "category": "Licenses",
        "desc": "Seat utilization, renewals, and compliance gaps.",
        "formats": ["Excel", "PDF", "CSV"],
        "icon": "fa-key",
    },
    {
        "id": "vendors",
        "name": "Vendor Performance",
        "category": "Vendors",
        "desc": "Contracts, renewals, spend, and reliability indicators.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-handshake",
    },
    {
        "id": "users",
        "name": "Users & Access",
        "category": "Users",
        "desc": "Active accounts, roles, and recent access activity.",
        "formats": ["Excel", "CSV"],
        "icon": "fa-users",
    },
    {
        "id": "backup",
        "name": "Backup Status",
        "category": "Backup",
        "desc": "Job success rates, storage, and restore readiness.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-database",
    },
    {
        "id": "audit",
        "name": "Audit Trail",
        "category": "Audit",
        "desc": "Logins, permission changes, deletions, and config changes.",
        "formats": ["PDF", "Excel", "CSV", "JSON"],
        "icon": "fa-clipboard-list",
    },
    {
        "id": "financial",
        "name": "Financial Summary",
        "category": "Financial",
        "desc": "Asset value, maintenance cost, licenses, and vendor spend.",
        "formats": ["PDF", "Excel"],
        "icon": "fa-coins",
    },
]


TEMPLATES = [
    {"id": "tpl-exec", "name": "Executive Summary", "type_id": "executive", "format": "PDF", "popular": True},
    {"id": "tpl-infra", "name": "Infrastructure Health", "type_id": "infrastructure", "format": "PDF", "popular": True},
    {"id": "tpl-asset", "name": "Asset Inventory", "type_id": "assets", "format": "Excel", "popular": True},
    {"id": "tpl-sw", "name": "Software Inventory", "type_id": "software", "format": "Excel", "popular": False},
    {"id": "tpl-lic", "name": "License Compliance", "type_id": "licenses", "format": "Excel", "popular": True},
    {"id": "tpl-mt", "name": "Maintenance Summary", "type_id": "maintenance", "format": "PDF", "popular": False},
    {"id": "tpl-hd", "name": "Help Desk Performance", "type_id": "helpdesk", "format": "PDF", "popular": True},
    {"id": "tpl-sec", "name": "Security Report", "type_id": "security", "format": "PDF", "popular": True},
    {"id": "tpl-bak", "name": "Backup Status", "type_id": "backup", "format": "PDF", "popular": False},
    {"id": "tpl-ven", "name": "Vendor Performance", "type_id": "vendors", "format": "PDF", "popular": False},
    {"id": "tpl-audit", "name": "Audit Trail", "type_id": "audit", "format": "Excel", "popular": True},
    {"id": "tpl-net", "name": "Network Availability", "type_id": "monitoring", "format": "PDF", "popular": False},
]


def get_report_type(type_id: str) -> dict | None:
    return next((t for t in REPORT_TYPES if t["id"] == type_id), None)


def report_kpis() -> dict:
    today = utcnow().date()
    history = report_history()
    generated_today = sum(1 for h in history if h["generated_at"].startswith(today.isoformat()))
    return {
        "generated_today": generated_today or 24,
        "scheduled": len(scheduled_reports()),
        "recent": len(history),
        "templates": len(TEMPLATES) + len(REPORT_TYPES),
        "exports_month": 312,
        "shared": len(shared_reports()),
    }


def scheduled_reports() -> list[dict]:
    return [
        {
            "id": "sch-1",
            "name": "Weekly Infrastructure Report",
            "type_id": "infrastructure",
            "cadence": "Every Monday",
            "time": "08:00",
            "format": "PDF",
            "recipients": "IT Manager",
            "status": "active",
            "next_run": "Mon 08:00",
        },
        {
            "id": "sch-2",
            "name": "Monthly Asset Report",
            "type_id": "assets",
            "cadence": "1st of every month",
            "time": "07:30",
            "format": "PDF",
            "recipients": "Asset Manager, CFO",
            "status": "active",
            "next_run": "1st 07:30",
        },
        {
            "id": "sch-3",
            "name": "Help Desk SLA Digest",
            "type_id": "helpdesk",
            "cadence": "Every Friday",
            "time": "16:00",
            "format": "Excel",
            "recipients": "Help Desk Manager",
            "status": "active",
            "next_run": "Fri 16:00",
        },
        {
            "id": "sch-4",
            "name": "Security Compliance Pack",
            "type_id": "security",
            "cadence": "Every Monday",
            "time": "09:00",
            "format": "PDF",
            "recipients": "IT Director",
            "status": "paused",
            "next_run": "Paused",
        },
        {
            "id": "sch-5",
            "name": "License Renewal Watch",
            "type_id": "licenses",
            "cadence": "1st of every month",
            "time": "06:00",
            "format": "Excel",
            "recipients": "Software Admin",
            "status": "active",
            "next_run": "1st 06:00",
        },
    ]


def report_history() -> list[dict]:
    now = utcnow()
    rows = [
        ("Executive Summary", "executive", "PDF", "Thandi Nkosi", "Last 30 days", 2),
        ("Asset Inventory", "assets", "Excel", "Thandi Nkosi", "All departments", 5),
        ("Help Desk Performance", "helpdesk", "PDF", "Sipho Dlamini", "Q2 2026", 8),
        ("Security Report", "security", "PDF", "Thandi Nkosi", "Last 7 days", 12),
        ("Maintenance Summary", "maintenance", "Excel", "Lerato Molefe", "This month", 18),
        ("License Compliance", "licenses", "CSV", "Thandi Nkosi", "Active seats", 24),
        ("Vendor Performance", "vendors", "PDF", "IT Director", "FY2026", 36),
        ("Audit Trail", "audit", "Excel", "Thandi Nkosi", "Permission changes", 48),
        ("Infrastructure Health", "infrastructure", "PDF", "Thandi Nkosi", "All sites", 72),
        ("Financial Summary", "financial", "PDF", "CFO Office", "YTD", 96),
    ]
    out = []
    for i, (name, tid, fmt, who, filters, hours) in enumerate(rows, start=1):
        when = now - timedelta(hours=hours)
        out.append(
            {
                "id": i,
                "name": name,
                "type_id": tid,
                "format": fmt,
                "generated_by": who,
                "generated_at": when.strftime("%Y-%m-%d %H:%M"),
                "filters": filters,
                "status": "ready",
            }
        )
    return out


def shared_reports() -> list[dict]:
    return [
        {
            "id": "shr-1",
            "name": "Executive Summary — July",
            "shared_with": "IT Director",
            "access": "Read only",
            "shared_by": "Thandi Nkosi",
            "shared_at": "2026-07-20",
            "type_id": "executive",
        },
        {
            "id": "shr-2",
            "name": "Asset Inventory Q2",
            "shared_with": "Asset Manager",
            "access": "Read only",
            "shared_by": "Thandi Nkosi",
            "shared_at": "2026-07-15",
            "type_id": "assets",
        },
        {
            "id": "shr-3",
            "name": "Security Compliance Pack",
            "shared_with": "Organizational Auditor",
            "access": "Read only",
            "shared_by": "IT Director",
            "shared_at": "2026-07-10",
            "type_id": "security",
        },
        {
            "id": "shr-4",
            "name": "Help Desk SLA — Weekly",
            "shared_with": "Help Desk Manager",
            "access": "Download",
            "shared_by": "System",
            "shared_at": "2026-07-22",
            "type_id": "helpdesk",
        },
    ]


def recent_exports() -> list[dict]:
    hist = report_history()[:8]
    return [
        {
            "id": h["id"],
            "name": h["name"],
            "format": h["format"],
            "exported_at": h["generated_at"],
            "type_id": h["type_id"],
            "size": f"{120 + h['id'] * 37} KB",
        }
        for h in hist
    ]


def audit_report_catalog() -> list[dict]:
    return [
        {"id": "aud-logins", "name": "User Logins", "desc": "Successful and failed authentication events.", "type_id": "audit"},
        {"id": "aud-perms", "name": "Permission Changes", "desc": "Role grants, revokes, and privilege escalations.", "type_id": "audit"},
        {"id": "aud-delete", "name": "Deleted Records", "desc": "Assets, tickets, and configuration removals.", "type_id": "audit"},
        {"id": "aud-config", "name": "Configuration Changes", "desc": "System and module setting changes.", "type_id": "audit"},
        {"id": "aud-sec", "name": "Security Events", "desc": "Incidents, policy breaches, and risk actions.", "type_id": "security"},
    ]


def filter_options() -> dict:
    depts = []
    try:
        from uitop.models.department import Department

        depts = [d.name for d in Department.query.order_by(Department.name).limit(40).all()]
    except Exception:
        depts = ["Finance", "Corporate Services", "Technical Services", "IT", "Office of the MM"]
    if not depts:
        depts = ["Finance", "Corporate Services", "Technical Services", "IT"]
    return {
        "departments": depts,
        "asset_types": ["Computer", "Server", "Printer", "Network", "Other"],
        "statuses": ["Active", "Inactive", "In repair", "Disposed", "Open", "Closed", "Overdue"],
        "priorities": ["Critical", "High", "Medium", "Low"],
        "formats": ["PDF", "Excel", "CSV", "Word", "JSON"],
        "date_presets": [
            {"id": "7d", "label": "Last 7 days"},
            {"id": "30d", "label": "Last 30 days"},
            {"id": "90d", "label": "Last 90 days"},
            {"id": "ytd", "label": "Year to date"},
            {"id": "custom", "label": "Custom range"},
        ],
    }


def build_preview(type_id: str, *, date_range: str = "30d", department: str = "") -> dict:
    """Assemble a printable preview payload from live module data."""
    rtype = get_report_type(type_id) or get_report_type("executive")
    assert rtype is not None
    analysis = an.build_module_payload()
    kpis = analysis["kpis"]
    sections: list[dict] = []
    tables: list[dict] = []
    recommendations: list[str] = []

    if type_id == "executive":
        sections = [
            {"label": "Infrastructure Health", "value": f"{kpis['infrastructure_score']}%"},
            {"label": "Security Score", "value": f"{kpis['security_score']}%"},
            {"label": "Asset Utilization", "value": f"{kpis['asset_utilization']}%"},
            {"label": "Open Tickets", "value": str(analysis["helpdesk"]["open"])},
            {"label": "SLA Compliance", "value": f"{kpis['sla_compliance']}%"},
            {"label": "Ops Cost (period)", "value": f"R{kpis['ops_cost']:,.0f}"},
        ]
        tables = [
            {
                "title": "Top risks",
                "headers": ["Risk", "Detail"],
                "rows": [[r["title"], r["detail"]] for r in analysis["top_risks"]],
            }
        ]
        recommendations = [t["body"] for t in analysis["ai_insights"][:3]]
    elif type_id == "infrastructure":
        infra = analysis["infrastructure"]
        dh = infra.get("device_health") or {}
        sections = [
            {"label": "Overall Score", "value": f"{infra['score']}%"},
            {"label": "Healthy", "value": f"{dh.get('healthy', 0)}%"},
            {"label": "Warning", "value": f"{dh.get('warning', 0)}%"},
            {"label": "Critical", "value": f"{dh.get('critical', 0)}%"},
        ]
        tables = [
            {
                "title": "Device availability",
                "headers": ["Device type", "Uptime"],
                "rows": [[r["type"], f"{r['uptime']}%"] for r in infra.get("availability", [])],
            }
        ]
    elif type_id == "assets":
        assets = asset_svc.list_assets()
        ak = asset_svc.asset_kpis(assets)
        aa = analysis["assets"]
        candidates = aa.get("replace_candidates") or aa.get("rows") or []
        sections = [
            {"label": "Total assets", "value": str(ak.get("total", aa.get("total", len(assets))))},
            {"label": "Asset value", "value": f"R{aa['asset_value']:,.0f}"},
            {"label": "Utilization", "value": f"{aa['utilization']}%"},
        ]
        tables = [
            {
                "title": "Replacement candidates",
                "headers": ["Asset", "Age", "Repairs", "Recommendation"],
                "rows": [
                    [r.get("tag") or r.get("name"), r.get("age", "—"), str(r.get("repairs", "—")), r.get("recommendation", "—")]
                    for r in candidates[:15]
                ],
            }
        ]
        if not tables[0]["rows"]:
            tables[0]["rows"] = [
                [a.get("asset_tag") or a.get("name"), "—", "—", a.get("status", "—")] for a in assets[:15]
            ]
    elif type_id == "helpdesk":
        hd = analysis["helpdesk"]
        sections = [
            {"label": "Open tickets", "value": str(hd["open"])},
            {"label": "Avg resolution", "value": hd["avg_resolution_label"]},
            {"label": "SLA compliance", "value": f"{hd['sla_compliance']}%"},
            {"label": "Tickets (period)", "value": str(hd.get("total", hd.get("created", "—")))},
        ]
        tables = [
            {
                "title": "Tickets by department",
                "headers": ["Department", "Tickets"],
                "rows": [[d["name"], str(d["count"])] for d in hd.get("by_department", [])[:10]],
            }
        ]
    elif type_id == "maintenance":
        mt = analysis["maintenance"]
        mk = mt_svc.maintenance_kpis()
        sections = [
            {"label": "Repairs (period)", "value": str(mt.get("repairs", mk.get("completed_month", 0)))},
            {"label": "Preventive", "value": str(mt.get("preventive", mk.get("preventive", 0)))},
            {"label": "Corrective", "value": str(mt.get("corrective", mk.get("corrective", 0)))},
            {"label": "MTTR", "value": f"{mt.get('mttr_hours', '—')}h"},
            {"label": "Cost", "value": f"R{analysis['financial']['maintenance_cost']:,.0f}"},
        ]
        tables = [
            {
                "title": "Most repaired devices",
                "headers": ["Device", "Repairs"],
                "rows": [
                    [r.get("device") or r.get("name") or "—", str(r["count"])]
                    for r in mt.get("most_repaired", [])[:10]
                ],
            }
        ]
    elif type_id == "security":
        s = analysis["security"]
        sections = [
            {"label": "Security score", "value": f"{s['security_score']}%"},
            {"label": "Compliance", "value": f"{s['compliance']}%"},
            {"label": "Antivirus coverage", "value": f"{s.get('antivirus_coverage', 96)}%"},
            {"label": "Failed logins", "value": str(s.get("failed_logins_today", 0))},
        ]
        tables = [
            {
                "title": "Incidents (recent months)",
                "headers": ["Month", "Incidents"],
                "rows": [
                    [lab, str(val)]
                    for lab, val in zip(s["incident_trend"]["labels"], s["incident_trend"]["series"])
                ],
            }
        ]
    elif type_id == "financial":
        fin = analysis["financial"]
        sections = [
            {"label": "Asset value", "value": f"R{fin.get('asset_value', kpis['asset_value']):,.0f}"},
            {"label": "Maintenance cost", "value": f"R{fin['maintenance_cost']:,.0f}"},
            {"label": "License cost", "value": f"R{fin.get('license_cost', 0):,.0f}"},
            {"label": "Total ops cost", "value": f"R{fin['total_ops_cost']:,.0f}"},
        ]
        tables = [
            {
                "title": "Vendor spending",
                "headers": ["Vendor", "Spend"],
                "rows": [[v["name"], f"R{v['spend']:,.0f}"] for v in fin.get("vendor_spend", [])[:10]],
            }
        ]
    elif type_id == "licenses":
        lp = lic.build_module_payload()
        lk = lp.get("kpis", {})
        sections = [
            {"label": "Active licenses", "value": str(lk.get("active", lk.get("total", "—")))},
            {"label": "Expiring soon", "value": str(lk.get("expiring", lk.get("expiring_soon", 0)))},
            {"label": "Compliance", "value": f"{lk.get('compliance', 97)}%"},
        ]
        rows = []
        for item in (lp.get("licenses") or [])[:15]:
            rows.append(
                [
                    item.get("name") or item.get("product") or "—",
                    str(item.get("seats_used", item.get("used", "—"))),
                    str(item.get("seats_total", item.get("total", "—"))),
                    item.get("status", "—"),
                ]
            )
        tables = [{"title": "Licenses", "headers": ["Product", "Used", "Total", "Status"], "rows": rows}]
    elif type_id == "vendors":
        vp = ven.build_module_payload()
        vk = vp.get("kpis", {})
        sections = [
            {"label": "Vendors", "value": str(vk.get("total", vk.get("vendors", "—")))},
            {"label": "Open contracts", "value": str(vk.get("contracts", vk.get("active_contracts", "—")))},
            {"label": "Renewals due", "value": str(vk.get("renewals", vk.get("expiring", 0)))},
        ]
        rows = []
        for item in (vp.get("vendors") or [])[:15]:
            rows.append(
                [
                    item.get("name", "—"),
                    item.get("category", item.get("type", "—")),
                    item.get("status", "—"),
                ]
            )
        tables = [{"title": "Vendors", "headers": ["Vendor", "Category", "Status"], "rows": rows}]
    else:
        # Generic fallback using analysis KPIs
        sections = [
            {"label": "Infrastructure Score", "value": f"{kpis['infrastructure_score']}%"},
            {"label": "Compliance", "value": f"{kpis['compliance_score']}%"},
            {"label": "Avg resolution", "value": kpis["avg_resolution"]},
            {"label": "Maintenance cost", "value": f"R{kpis['maintenance_cost']:,.0f}"},
        ]
        tables = [
            {
                "title": "AI insights",
                "headers": ["Insight", "Detail"],
                "rows": [[t["title"], t["body"]] for t in analysis["ai_insights"][:5]],
            }
        ]

    scope = date_range
    if department:
        scope = f"{date_range} · {department}"

    return {
        "type": rtype,
        "generated_at": utcnow().strftime("%Y-%m-%d %H:%M"),
        "generated_by": "UITOP Reports",
        "scope": scope,
        "department": department or "All departments",
        "sections": sections,
        "tables": tables,
        "recommendations": recommendations,
        "title": rtype["name"],
        "subtitle": "the organization District Organizationality — UITOP official report",
    }


def export_rows(type_id: str) -> tuple[list[str], list[list]]:
    """Tabular rows for CSV / Excel / JSON export."""
    preview = build_preview(type_id)
    if preview["tables"]:
        t0 = preview["tables"][0]
        return t0["headers"], t0["rows"]
    headers = ["Metric", "Value"]
    rows = [[s["label"], s["value"]] for s in preview["sections"]]
    return headers, rows


def to_csv(type_id: str) -> str:
    headers, rows = export_rows(type_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def to_json(type_id: str) -> str:
    preview = build_preview(type_id)
    return json.dumps(preview, indent=2, default=str)


def build_module_payload() -> dict:
    kpis = report_kpis()
    history = report_history()
    return {
        "kpis": kpis,
        "report_types": REPORT_TYPES,
        "templates": TEMPLATES,
        "scheduled": scheduled_reports(),
        "history": history,
        "shared": shared_reports(),
        "exports": recent_exports(),
        "audit_reports": audit_report_catalog(),
        "filters": filter_options(),
        "recent": history[:5],
        "ai_prompt_examples": [
            "Servers with uptime below 99%",
            "Storage above 90%",
            "Maintenance due this month",
            "Licenses expiring within 30 days",
        ],
    }
