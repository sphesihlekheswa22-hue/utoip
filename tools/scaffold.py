"""
Generate UITOP module templates + route blueprints.
Run: python tools/scaffold.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ROUTES = ROOT / "routes"

MODULES = {
    "computers": {
        "title": "Computers",
        "icon": "fa-desktop",
        "singular": "Computer",
        "pages": [
            "index", "create", "details", "edit", "delete",
            "performance", "software", "services", "event-logs",
            "network", "processes", "remote-access", "history",
        ],
        "kpis": [
            ("Online", "186", "+4 today", "success", "fa-signal"),
            ("Offline", "7", "Needs check", "danger", "fa-plug-circle-xmark"),
            ("Windows", "142", "76%", "default", "fa-windows"),
            ("Pending patches", "23", "This week", "warning", "fa-shield-halved"),
        ],
        "columns": ["Hostname", "User", "OS", "IP", "Status", "Last seen"],
        "rows": [
            ["PC-FIN-014", "S. Dlamini", "Windows 11", "10.12.4.88", "Online", "2 min ago"],
            ["PC-HR-003", "L. Mokoena", "Windows 10", "10.12.5.21", "Warning", "18 min ago"],
            ["PC-ENG-221", "J. Naidoo", "Windows 11", "10.12.8.14", "Online", "Just now"],
            ["LAP-EXE-009", "Mayor Office", "Windows 11", "10.12.1.9", "Offline", "6 hrs ago"],
            ["PC-LIB-044", "K. Zulu", "Ubuntu 22.04", "10.12.9.44", "Online", "5 min ago"],
        ],
    },
    "assets": {
        "title": "Assets",
        "icon": "fa-box",
        "singular": "Asset",
        "pages": [
            "index", "create", "edit", "details",
            "categories", "vendors", "requests", "assignments", "history",
        ],
        "kpis": [
            ("Total assets", "2,418", "+32 MoM", "default", "fa-boxes-stacked"),
            ("Assigned", "1,902", "78%", "success", "fa-user-check"),
            ("In store", "411", "Ready", "default", "fa-warehouse"),
            ("Maintenance", "105", "Scheduled", "warning", "fa-wrench"),
        ],
        "columns": ["Asset tag", "Name", "Category", "Assignee", "Status", "Location"],
        "rows": [
            ["AST-10021", "Dell Latitude 5540", "Laptop", "T. Nkosi", "Assigned", "HQ Floor 2"],
            ["AST-10088", "Cisco Catalyst 9200", "Network", "Infra Team", "Active", "DC Rack A"],
            ["AST-10102", "HP LaserJet Pro", "Printer", "Finance", "Active", "Finance Wing"],
            ["AST-10155", "iPhone 14", "Mobile", "Unassigned", "In store", "Stores"],
        ],
    },
    "users": {
        "title": "Users",
        "icon": "fa-users",
        "singular": "User",
        "pages": [
            "index", "create", "edit", "profile",
            "permissions", "activity", "sessions",
        ],
        "kpis": [
            ("Active users", "312", "+8 this month", "success", "fa-user-check"),
            ("Admins", "14", "Privileged", "warning", "fa-user-shield"),
            ("Locked", "3", "Review", "danger", "fa-lock"),
            ("MFA enabled", "89%", "Target 95%", "default", "fa-key"),
        ],
        "columns": ["Name", "Email", "Role", "Department", "Status", "Last login"],
        "rows": [
            ["Thandi Nkosi", "admin@umzinyathi.gov.za", "Super Admin", "IT", "Active", "Today"],
            ["Sipho Dlamini", "sipho.d@umzinyathi.gov.za", "Help Desk", "IT", "Active", "Today"],
            ["Lerato Mokoena", "lerato.m@umzinyathi.gov.za", "Dept Manager", "HR", "Active", "Yesterday"],
            ["Johan Botha", "j.botha@umzinyathi.gov.za", "Infra Eng", "IT", "Locked", "5 days ago"],
        ],
    },
    "servers": {
        "title": "Servers",
        "icon": "fa-server",
        "singular": "Server",
        "pages": ["index", "create", "details", "edit", "performance", "services", "history"],
        "kpis": [
            ("Healthy", "18", "All green", "success", "fa-heart-pulse"),
            ("Degraded", "2", "Investigate", "warning", "fa-triangle-exclamation"),
            ("CPU avg", "41%", "24h", "default", "fa-microchip"),
            ("Storage", "68%", "Used", "warning", "fa-hard-drive"),
        ],
        "columns": ["Name", "Role", "OS", "IP", "CPU", "Status"],
        "rows": [
            ["DC-AD-01", "Domain Controller", "Server 2022", "10.12.0.11", "22%", "Online"],
            ["APP-ERP-02", "ERP App", "Server 2019", "10.12.0.42", "67%", "Warning"],
            ["SQL-PROD-01", "SQL Cluster", "Server 2022", "10.12.0.55", "54%", "Online"],
        ],
    },
    "helpdesk": {
        "title": "Help Desk",
        "icon": "fa-life-ring",
        "singular": "Ticket",
        "pages": ["index", "create", "details", "edit", "history"],
        "kpis": [
            ("Open", "47", "12 high", "warning", "fa-ticket"),
            ("SLA breached", "3", "Escalate", "danger", "fa-clock"),
            ("Resolved today", "19", "+6 vs avg", "success", "fa-circle-check"),
            ("Avg response", "28m", "Within SLA", "default", "fa-bolt"),
        ],
        "columns": ["ID", "Subject", "Requester", "Priority", "Assignee", "Status"],
        "rows": [
            ["HD-2401", "VPN cannot connect", "K. Zulu", "High", "S. Dlamini", "Open"],
            ["HD-2398", "Printer jam Finance", "Finance Desk", "Medium", "Queue", "Pending"],
            ["HD-2390", "Laptop slow boot", "L. Mokoena", "Low", "J. Botha", "In progress"],
        ],
    },
    "monitoring": {
        "title": "Monitoring",
        "icon": "fa-chart-line",
        "singular": "Monitor",
        "pages": ["index", "details", "history"],
        "kpis": [
            ("Uptime", "99.94%", "30 days", "success", "fa-signal"),
            ("Active alerts", "8", "2 critical", "danger", "fa-bell"),
            ("Agents", "214", "Reporting", "default", "fa-satellite-dish"),
            ("Latency", "18ms", "Core LAN", "success", "fa-gauge-high"),
        ],
        "columns": ["Host", "Metric", "Value", "Threshold", "Status", "Updated"],
        "rows": [
            ["DC-AD-01", "CPU", "22%", "85%", "Healthy", "1 min"],
            ["APP-ERP-02", "Memory", "91%", "90%", "Critical", "1 min"],
            ["FW-EDGE-01", "Sessions", "4.2k", "8k", "Healthy", "30 sec"],
        ],
    },
    "backup": {
        "title": "Backup Center",
        "icon": "fa-hard-drive",
        "singular": "Backup job",
        "pages": ["index", "create", "details", "edit", "history"],
        "kpis": [
            ("Successful", "96%", "Last 7 days", "success", "fa-circle-check"),
            ("Failed", "2", "Retry queued", "danger", "fa-circle-xmark"),
            ("Protected TB", "48.2", "Across sites", "default", "fa-database"),
            ("Next window", "22:00", "Nightly", "default", "fa-moon"),
        ],
        "columns": ["Job", "Target", "Type", "Last run", "Size", "Status"],
        "rows": [
            ["SQL Full", "SQL-PROD-01", "Full", "Tonight 01:12", "420 GB", "Success"],
            ["File Shares", "NAS-01", "Incremental", "Tonight 02:40", "18 GB", "Success"],
            ["DC System State", "DC-AD-01", "Full", "Failed 03:01", "—", "Failed"],
        ],
    },
    "ai": {
        "title": "AI Assistant",
        "icon": "fa-sparkles",
        "singular": "Session",
        "pages": ["index", "history"],
        "kpis": [
            ("Sessions today", "64", "+12%", "default", "fa-comments"),
            ("Suggestions accepted", "71%", "Ops", "success", "fa-thumbs-up"),
            ("Incidents assisted", "9", "Open tickets", "warning", "fa-life-ring"),
            ("Avg resolve assist", "6m", "Faster triage", "success", "fa-stopwatch"),
        ],
        "columns": ["Session", "User", "Topic", "Messages", "Outcome", "When"],
        "rows": [
            ["AI-8841", "S. Dlamini", "VPN troubleshooting", "12", "Resolved", "10:14"],
            ["AI-8830", "T. Nkosi", "License expiry report", "5", "Report ready", "09:40"],
        ],
    },
}

# Remaining modules with lighter default pages
EXTRA = {
    "network": ("Network Devices", "fa-network-wired", ["index", "create", "details", "edit", "history"]),
    "printers": ("Printers", "fa-print", ["index", "create", "details", "edit", "history"]),
    "software": ("Software", "fa-cubes", ["index", "create", "details", "edit", "history"]),
    "licenses": ("Licenses", "fa-key", ["index", "create", "details", "edit", "history"]),
    "vendors": ("Vendors", "fa-handshake", ["index", "create", "details", "edit", "history"]),
    "restore": ("Restore Center", "fa-rotate-left", ["index", "create", "details", "history"]),
    "alerts": ("Alerts", "fa-bell", ["index", "details", "history"]),
    "knowledge": ("Knowledge Base", "fa-book-open", ["index", "create", "details", "edit"]),
    "maintenance": ("Maintenance", "fa-wrench", ["index", "create", "details", "edit", "history"]),
    "documents": ("Documents", "fa-folder-open", ["index", "create", "details", "edit"]),
    "files": ("File Manager", "fa-folder", ["index", "details"]),
    "analytics": ("Analytics", "fa-chart-column", ["index", "details"]),
    "reports": ("Reports", "fa-file-lines", ["index", "create", "details"]),
    "roles": ("Roles", "fa-shield-halved", ["index", "create", "edit", "details"]),
    "departments": ("Departments", "fa-building", ["index", "create", "edit", "details"]),
    "notifications": ("Notifications", "fa-bell", ["index"]),
    "profile": ("Profile", "fa-user", ["index", "edit"]),
    "settings": ("Settings", "fa-gear", ["index"]),
    "audit": ("Audit Logs", "fa-clipboard-list", ["index", "details"]),
    "calendar": ("Calendar", "fa-calendar-days", ["index", "create", "details"]),
    "security": ("Security / Vault", "fa-vault", ["index", "create", "details"]),
    "search": ("Search", "fa-magnifying-glass", ["index"]),
}


INDEX_TMPL = '''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import page_header, kpi_card, filter_bar, status_badge, pagination %}}

{{% block title %}}{title}{{% endblock %}}
{{% block page_title %}}{title}{{% endblock %}}

{{% block content %}}
{{% call page_header("{title}", "{subtitle}", "{create_href}", "Add {singular}", "{icon}") %}}{{% endcall %}}

<div class="kpi-grid">
{kpis}
</div>

{{% call filter_bar("Search {title_lower}…") %}}
  <button type="button" class="btn btn-secondary btn-sm"><i class="fas fa-filter"></i> Filters</button>
  <button type="button" class="btn btn-ghost btn-sm"><i class="fas fa-download"></i> Export</button>
{{% endcall %}}

<section class="table-panel panel">
  <div class="table-scroll">
    <table class="data-table">
      <thead>
        <tr>
{thead}
          <th></th>
        </tr>
      </thead>
      <tbody>
{tbody}
      </tbody>
    </table>
  </div>
  {{{{ pagination(1, 4) }}}}
</section>
{{% endblock %}}
'''

CREATE_TMPL = '''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import page_header, form_field %}}

{{% block title %}}New {singular}{{% endblock %}}
{{% block page_title %}}New {singular}{{% endblock %}}

{{% block content %}}
{{% call page_header("New {singular}", "Capture {singular_lower} details for UITOP inventory.") %}}{{% endcall %}}

<form class="panel form-panel" method="post" data-validate>
  <div class="form-grid">
    {{{{ form_field("name", "Name", required=True, placeholder="{singular} name") }}}}
    {{{{ form_field("code", "Code / Tag", placeholder="Auto or manual") }}}}
    {{{{ form_field("owner", "Owner / Assignee") }}}}
    {{{{ form_field("location", "Location") }}}}
    {{{{ form_field("notes", "Notes", type="textarea", placeholder="Optional notes") }}}}
  </div>
  <div class="form-actions">
    <a href="{index_href}" class="btn btn-secondary">Cancel</a>
    <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Save {singular}</button>
  </div>
</form>
{{% endblock %}}
'''

EDIT_TMPL = '''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import page_header, form_field %}}

{{% block title %}}Edit {singular}{{% endblock %}}
{{% block page_title %}}Edit {singular}{{% endblock %}}

{{% block content %}}
{{% call page_header("Edit {singular}", "Update inventory and ownership details.") %}}{{% endcall %}}

<form class="panel form-panel" method="post" data-validate>
  <div class="form-grid">
    {{{{ form_field("name", "Name", value=item.name if item is defined else "Demo {singular}", required=True) }}}}
    {{{{ form_field("status", "Status", value="Active") }}}}
    {{{{ form_field("owner", "Owner", value="IT Operations") }}}}
    {{{{ form_field("notes", "Notes", type="textarea", value="Updated via UITOP demo.") }}}}
  </div>
  <div class="form-actions">
    <a href="{index_href}" class="btn btn-secondary">Cancel</a>
    <button type="submit" class="btn btn-primary">Save changes</button>
  </div>
</form>
{{% endblock %}}
'''

DETAILS_TMPL = '''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import page_header, status_badge, detail_row %}}

{{% block title %}}{singular} details{{% endblock %}}
{{% block page_title %}}{singular} details{{% endblock %}}

{{% block content %}}
{{% call page_header("{singular} details", "Operational profile and related activity.", "{edit_href}", "Edit", "fa-pen") %}}{{% endcall %}}

<div class="detail-layout">
  <section class="panel detail-card">
    <header class="card-header">
      <h2>Overview</h2>
      {{{{ status_badge("Online") }}}}
    </header>
    <dl class="detail-list">
      {{{{ detail_row("Name", "Demo {singular} 01") }}}}
      {{{{ detail_row("Identifier", "UITOP-DEMO-001") }}}}
      {{{{ detail_row("Owner", "IT Operations") }}}}
      {{{{ detail_row("Department", "Corporate Services") }}}}
      {{{{ detail_row("Last updated", "Today 09:42") }}}}
    </dl>
  </section>
  <section class="panel detail-card">
    <header class="card-header"><h2>Related</h2></header>
    <ul class="related-list">
      <li><a href="{index_href}">Back to {title}</a></li>
      <li><a href="{{{{ url_for('monitoring.index') }}}}">Open monitoring</a></li>
      <li><a href="{{{{ url_for('ai.index') }}}}">Ask AI about this record</a></li>
    </ul>
  </section>
</div>
{{% endblock %}}
'''

SUBPAGE_TMPL = '''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import page_header, status_badge %}}

{{% block title %}}{page_title}{{% endblock %}}
{{% block page_title %}}{page_title}{{% endblock %}}

{{% block content %}}
{{% call page_header("{page_title}", "{page_sub}", "{index_href}", "Back to list", "fa-arrow-left") %}}{{% endcall %}}

<section class="panel detail-card">
  <header class="card-header">
    <h2>{page_title}</h2>
    {{{{ status_badge("Active") }}}}
  </header>
  <div class="subpage-body">
    <p class="page-subtitle">{page_blurb}</p>
    <div class="kpi-grid compact">
      <article class="kpi-card"><div class="kpi-body"><p class="kpi-label">Samples</p><p class="kpi-value">12</p></div></article>
      <article class="kpi-card"><div class="kpi-body"><p class="kpi-label">Healthy</p><p class="kpi-value">9</p></div></article>
      <article class="kpi-card"><div class="kpi-body"><p class="kpi-label">Attention</p><p class="kpi-value">3</p></div></article>
    </div>
    <div class="table-scroll" style="margin-top:1rem;">
      <table class="data-table">
        <thead><tr><th>Item</th><th>Detail</th><th>Status</th><th>Updated</th></tr></thead>
        <tbody>
          <tr><td>Sample metric A</td><td>Within range</td><td>{{{{ status_badge("Healthy") }}}}</td><td>2 min ago</td></tr>
          <tr><td>Sample metric B</td><td>Needs review</td><td>{{{{ status_badge("Warning") }}}}</td><td>8 min ago</td></tr>
          <tr><td>Sample metric C</td><td>Nominal</td><td>{{{{ status_badge("Online") }}}}</td><td>Just now</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>
{{% endblock %}}
'''


def kpi_html(kpis):
    lines = []
    for label, value, delta, tone, icon in kpis:
        lines.append(
            f'  {{{{ kpi_card("{label}", "{value}", "{delta}", "{tone}", "{icon}") }}}}'
        )
    return "\n".join(lines)


def thead_html(cols):
    return "\n".join(f"          <th>{c}</th>" for c in cols)


def tbody_html(rows, details_href):
    out = []
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row[:-1])
        status = row[-1]
        # last col might not be status - for our data last is often status-ish; use second last if Status column
        # Simpler: render all cells, badge the Status-like values
        cells = []
        for i, c in enumerate(row):
            if c.lower() in {
                "online", "offline", "warning", "active", "assigned", "in store",
                "success", "failed", "open", "pending", "in progress", "healthy",
                "critical", "locked",
            }:
                cells.append(f"<td>{{{{ status_badge('{c}') }}}}</td>")
            else:
                cells.append(f"<td>{c}</td>")
        out.append(
            "        <tr>\n          "
            + "\n          ".join(cells)
            + f'\n          <td class="row-actions"><a class="btn btn-ghost btn-sm" href="{details_href}">View</a></td>\n        </tr>'
        )
    return "\n".join(out)


def write_module(key, meta, dedicated_route=True):
    folder = TEMPLATES / key
    folder.mkdir(parents=True, exist_ok=True)
    title = meta["title"]
    singular = meta["singular"]
    icon = meta.get("icon", "fa-cube")
    pages = meta["pages"]
    if dedicated_route:
        index_href = f"{{{{ url_for('{key}.index') }}}}"
        create_href = f"{{{{ url_for('{key}.create') }}}}"
        edit_href = f"{{{{ url_for('{key}.edit', item_id=1) }}}}"
        details_href = f"{{{{ url_for('{key}.details', item_id=1) }}}}"
    else:
        index_href = f"{{{{ url_for('modules.page', module='{key}', page='index') }}}}"
        create_href = f"{{{{ url_for('modules.page', module='{key}', page='create') }}}}"
        edit_href = f"{{{{ url_for('modules.page', module='{key}', page='edit') }}}}"
        details_href = f"{{{{ url_for('modules.page', module='{key}', page='details') }}}}"

    kpis = meta.get("kpis") or [
        ("Total", "128", "+3%", "default", icon),
        ("Active", "110", "Healthy", "success", "fa-circle-check"),
        ("Attention", "12", "Review", "warning", "fa-triangle-exclamation"),
        ("Critical", "6", "Urgent", "danger", "fa-bolt"),
    ]
    cols = meta.get("columns") or ["Name", "Owner", "Type", "Updated", "Status"]
    rows = meta.get("rows") or [
        [f"Demo {singular} 1", "IT Ops", "Standard", "Today", "Active"],
        [f"Demo {singular} 2", "Infrastructure", "Critical", "Yesterday", "Warning"],
        [f"Demo {singular} 3", "Help Desk", "Standard", "2 days ago", "Online"],
    ]

    for page in pages:
        path = folder / f"{page}.html"
        if page == "index":
            content = INDEX_TMPL.format(
                title=title,
                title_lower=title.lower(),
                subtitle=f"Manage {title.lower()} across Umzinyathi IT operations.",
                create_href=create_href if "create" in pages else index_href,
                singular=singular,
                icon="fa-plus",
                kpis=kpi_html(kpis),
                thead=thead_html(cols),
                tbody=tbody_html(rows, details_href if "details" in pages else index_href),
            )
        elif page == "create":
            content = CREATE_TMPL.format(
                singular=singular,
                singular_lower=singular.lower(),
                index_href=index_href,
            )
        elif page == "edit":
            content = EDIT_TMPL.format(singular=singular, index_href=index_href)
        elif page == "details":
            content = DETAILS_TMPL.format(
                singular=singular,
                title=title,
                edit_href=edit_href if "edit" in pages else index_href,
                index_href=index_href,
            )
        elif page == "delete":
            content = SUBPAGE_TMPL.format(
                page_title=f"Delete {singular}",
                page_sub="Confirm removal from UITOP inventory.",
                page_blurb="Deleting removes this record from active operations views. Audit history is retained.",
                index_href=index_href,
            )
        else:
            nice = page.replace("-", " ").title()
            content = SUBPAGE_TMPL.format(
                page_title=f"{singular} · {nice}",
                page_sub=f"{nice} insights for this {singular.lower()}.",
                page_blurb=f"Live and historical {nice.lower()} data for operations teams.",
                index_href=index_href,
            )
        path.write_text(content, encoding="utf-8")


def write_dedicated_route(key: str):
    pages = MODULES[key]["pages"]
    lines = [
        f'"""Routes for {key} module."""',
        "from flask import Blueprint, render_template, redirect, url_for, flash",
        "",
        f'bp = Blueprint("{key}", __name__, url_prefix="/{key}")',
        "",
        "",
        "@bp.get('/')",
        "def index():",
        f'    return render_template("{key}/index.html", active="{key}")',
        "",
    ]
    if "create" in pages:
        lines += [
            "",
            "@bp.route('/create', methods=['GET', 'POST'])",
            "def create():",
            "    # Demo: accept POST and return to list",
            "    from flask import request",
            "    if request.method == 'POST':",
            '        flash("Saved (demo mode).", "success")',
            f'        return redirect(url_for("{key}.index"))',
            f'    return render_template("{key}/create.html", active="{key}")',
            "",
        ]
    if "details" in pages:
        lines += [
            "",
            "@bp.get('/<int:item_id>')",
            "def details(item_id):",
            f'    return render_template("{key}/details.html", active="{key}", item_id=item_id)',
            "",
        ]
    if "edit" in pages:
        lines += [
            "",
            "@bp.route('/<int:item_id>/edit', methods=['GET', 'POST'])",
            "def edit(item_id):",
            "    from flask import request",
            "    if request.method == 'POST':",
            '        flash("Updated (demo mode).", "success")',
            f'        return redirect(url_for("{key}.details", item_id=item_id))',
            f'    return render_template("{key}/edit.html", active="{key}", item_id=item_id)',
            "",
        ]
    for page in pages:
        if page in {"index", "create", "details", "edit"}:
            continue
        slug = page
        lines += [
            "",
            f"@bp.get('/<int:item_id>/{slug}')",
            f"def {slug.replace('-', '_')}(item_id):",
            f'    return render_template("{key}/{slug}.html", active="{key}", item_id=item_id)',
            "",
        ]
    (ROUTES / f"{key}.py").write_text("\n".join(lines), encoding="utf-8")


def main():
    for key, meta in MODULES.items():
        write_module(key, meta, dedicated_route=True)
        write_dedicated_route(key)

    for key, (title, icon, pages) in EXTRA.items():
        if key in MODULES:
            continue
        # skip if dedicated special-cased later
        if key in {"analytics", "reports", "restore", "settings", "monitoring"}:
            # still generate templates; routes may be dedicated stubs
            pass
        write_module(
            key,
            {
                "title": title,
                "icon": icon,
                "singular": title.rstrip("s") if title.endswith("s") else title,
                "pages": pages,
            },
            dedicated_route=False,
        )

    # modules catch-all route
    modules_py = '''"""Generic module page renderer for scaffolded templates."""
from flask import Blueprint, abort, render_template

bp = Blueprint("modules", __name__)

ALLOWED = {
'''
    allowed = []
    for key, (_, _, pages) in EXTRA.items():
        allowed.append(f'    "{key}": {pages!r},')
    # also allow gold modules pages via modules if needed
    modules_py += "\n".join(allowed) + "\n}\n\n\n"
    modules_py += '''@bp.get("/m/<module>/<page>")
def page(module, page):
    pages = ALLOWED.get(module)
    if not pages or page not in pages:
        abort(404)
    return render_template(f"{module}/{page}.html", active=module)


# Friendly aliases matching sidebar URLs for extra modules
'''
    for key in EXTRA:
        modules_py += f'''

@bp.get("/{key}/")
def {key}_index():
    return page("{key}", "index")
'''
    (ROUTES / "modules.py").write_text(modules_py, encoding="utf-8")
    print("Scaffold complete.")


if __name__ == "__main__":
    main()
