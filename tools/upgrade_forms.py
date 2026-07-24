"""Upgrade scaffold + live form templates to professional uf-form shell."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"C:\Users\Zoey\OneDrive\Documents\My Web Apps\NewUITOP\templates")

# Live modules we rewrite by hand — skip in scaffold batch
SKIP = {
    "helpdesk/create.html",
    "helpdesk/edit.html",
    "users/create.html",
    "users/edit.html",
    "assets/create.html",
    "assets/edit.html",
    "assets/link.html",
    "assets/request.html",
    "auth/login.html",
    "profile/edit.html",
}

MODULE_META = {
    "computers": ("Computer", "fa-desktop", "computers.index", "Endpoint inventory"),
    "servers": ("Server", "fa-server", "servers.index", "Server inventory"),
    "network": ("Network device", "fa-network-wired", "network.index", "Network inventory"),
    "printers": ("Printer", "fa-print", "printers.index", "Printer inventory"),
    "backup": ("Backup job", "fa-database", "backup.index", "Backup operations"),
    "software": ("Software", "fa-cubes", "modules.software_index", "Software catalogue"),
    "licenses": ("License", "fa-key", "modules.licenses_index", "License management"),
    "vendors": ("Vendor", "fa-building", "modules.vendors_index", "Vendor directory"),
    "restore": ("Restore job", "fa-clock-rotate-left", "restore.index", "Restore operations"),
    "knowledge": ("Article", "fa-book", "modules.knowledge_index", "Knowledge base"),
    "maintenance": ("Maintenance", "fa-wrench", "modules.maintenance_index", "Maintenance window"),
    "documents": ("Document", "fa-file-lines", "modules.documents_index", "Document library"),
    "reports": ("Report", "fa-chart-pie", "reports.index", "Reporting"),
    "roles": ("Role", "fa-user-shield", "modules.roles_index", "Access control"),
    "departments": ("Department", "fa-sitemap", "modules.departments_index", "Organisation"),
    "calendar": ("Event", "fa-calendar", "modules.calendar_index", "IT calendar"),
    "security": ("Security item", "fa-shield-halved", "modules.security_index", "Security"),
}


def create_tpl(module: str, singular: str, icon: str, index_ep: str, eyebrow: str) -> str:
    return f'''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import form_field %}}

{{% block title %}}New {singular}{{% endblock %}}
{{% block page_title %}}New {singular}{{% endblock %}}

{{% block content %}}
<div class="uf-page uf-page--single">
  <header class="uf-hero">
    <div class="uf-hero-inner">
      <div>
        <p class="uf-eyebrow"><i class="fas {icon}"></i> {eyebrow}</p>
        <h1>New {singular}</h1>
        <p>Capture clear details so operations stays accurate and searchable.</p>
      </div>
      <div class="uf-hero-meta">
        <span class="uf-chip"><i class="fas fa-pen-to-square"></i> Guided form</span>
      </div>
    </div>
  </header>

  <form class="uf-card" method="post" data-validate>
    <section class="uf-section">
      <div class="uf-section-head">
        <span class="uf-section-num">1</span>
        <div>
          <h2>Details</h2>
          <p>Required fields first — extras when you have them.</p>
        </div>
      </div>
      <div class="uf-section-body">
        <div class="form-grid uf-form-grid">
          {{{{ form_field("name", "Name", required=True, placeholder="{singular} name") }}}}
          {{{{ form_field("code", "Code / Tag", placeholder="Auto or manual") }}}}
          {{{{ form_field("owner", "Owner / Assignee") }}}}
          {{{{ form_field("location", "Location") }}}}
          {{{{ form_field("notes", "Notes", type="textarea", placeholder="Optional notes") }}}}
        </div>
      </div>
    </section>
    <div class="uf-actions">
      <a href="{{{{ url_for('{index_ep}') }}}}" class="btn btn-secondary">Cancel</a>
      <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Save {singular}</button>
    </div>
  </form>
</div>
{{% endblock %}}
'''


def edit_tpl(module: str, singular: str, icon: str, index_ep: str, eyebrow: str) -> str:
    return f'''{{% extends "layouts/base.html" %}}
{{% from "components/macros.html" import form_field %}}

{{% block title %}}Edit {singular}{{% endblock %}}
{{% block page_title %}}Edit {singular}{{% endblock %}}

{{% block content %}}
<div class="uf-page uf-page--single">
  <header class="uf-hero">
    <div class="uf-hero-inner">
      <div>
        <p class="uf-eyebrow"><i class="fas {icon}"></i> {eyebrow}</p>
        <h1>Edit {singular}</h1>
        <p>Update inventory and ownership details.</p>
      </div>
    </div>
  </header>

  <form class="uf-card" method="post" data-validate>
    <section class="uf-section">
      <div class="uf-section-head">
        <span class="uf-section-num">1</span>
        <div>
          <h2>Details</h2>
          <p>Keep records current for audits and support.</p>
        </div>
      </div>
      <div class="uf-section-body">
        <div class="form-grid uf-form-grid">
          {{{{ form_field("name", "Name", value=item.name if item is defined else "Demo {singular}", required=True) }}}}
          {{{{ form_field("status", "Status", value="Active") }}}}
          {{{{ form_field("owner", "Owner", value="IT Operations") }}}}
          {{{{ form_field("notes", "Notes", type="textarea", value="Updated via UITOP.") }}}}
        </div>
      </div>
    </section>
    <div class="uf-actions">
      <a href="{{{{ url_for('{index_ep}') }}}}" class="btn btn-secondary">Cancel</a>
      <button type="submit" class="btn btn-primary">Save changes</button>
    </div>
  </form>
</div>
{{% endblock %}}
'''


def main():
    updated = []
    for module, (singular, icon, index_ep, eyebrow) in MODULE_META.items():
        c = ROOT / module / "create.html"
        e = ROOT / module / "edit.html"
        if c.exists() and f"{module}/create.html" not in SKIP:
            c.write_text(create_tpl(module, singular, icon, index_ep, eyebrow), encoding="utf-8")
            updated.append(str(c.relative_to(ROOT)))
        if e.exists() and f"{module}/edit.html" not in SKIP:
            e.write_text(edit_tpl(module, singular, icon, index_ep, eyebrow), encoding="utf-8")
            updated.append(str(e.relative_to(ROOT)))
    print(f"Updated {len(updated)} templates")
    for u in updated:
        print(" ", u)


if __name__ == "__main__":
    main()
