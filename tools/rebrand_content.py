"""One-off content rebrand: municipality-specific → universal UITOP (safe text swaps)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "node_modules", ".venv", "__pycache__", "migrations/versions"}

TARGET_DIRS = ("templates", "static/css")
EXTRA_FILES = ("README.md", "DEPLOY_RENDER.md", "REQUIREMENTS.md", "desktop_app.py")

# Templates/static: prefer Jinja branding variables where shown to users.
TEMPLATE_REPLACEMENTS: list[tuple[str, str]] = [
    ("Umzinyathi IT Operations Platform", "UITOP — Unified IT Operations Platform"),
    ("UMZINYATHI IT OPERATIONS PLATFORM", "UITOP — UNIFIED IT OPERATIONS PLATFORM"),
    ("Umzinyathi District Municipality", "{{ org_name }}"),
    ("Umzinyathi Municipality", "{{ org_name }}"),
    ("Umzinyathi", "{{ org_name }}"),
    ("@umzinyathi.gov.za", "@{{ org_email_domain }}"),
    ("umzinyathi.gov.za", "{{ org_email_domain }}"),
    ("UMZINYATHI.LOCAL", "CORP.LOCAL"),
    ("uitop.umzinyathi.gov.za", "uitop.example.com"),
    ("MUNICIPAL OPERATIONS PLATFORM", "UNIFIED IT OPERATIONS PLATFORM"),
    ("municipal IT", "workplace IT"),
    ("Municipal IT", "Workplace IT"),
    ("municipal ", "organizational "),
    ("Municipal ", "Organizational "),
    ("municipality ", "organization "),
    ("municipality.", "organization."),
    ("the municipality", "your organization"),
    ("the municipal", "the organizational"),
    ("Municipality ", "Organization "),
    ("municipality", "organization"),
    ("Municipal", "Organizational"),
    ("municipal", "organizational"),
    ("Municipality", "Organization"),
    ("Municipal Teal", "UITOP Teal"),
    ("Municipal teal", "UITOP teal"),
    ("Municipal EA", "Enterprise agreement"),
    ("Kaspersky Municipal Bundle", "Kaspersky Endpoint Bundle"),
    ("across Umzinyathi IT operations", "across your IT operations"),
    ("Manage restore center across Umzinyathi IT operations.", "Manage restore operations across your organization."),
    ("Manage analytics across Umzinyathi IT operations.", "Manage analytics across your organization."),
    ("Manage roles across Umzinyathi IT operations.", "Manage roles across your organization."),
    ("Manage departments across Umzinyathi IT operations.", "Manage departments and branches across your organization."),
    ("Manage search across Umzinyathi IT operations.", "Search across your IT environment."),
    ("Powering Operations. Strengthening Umzinyathi.", "{{ app_tagline }}."),
    ("Smart Operations<br>for a Better <em>Umzinyathi</em>", "Unified IT Operations<br>for <em>Your Organization</em>"),
    ("A unified platform to manage assets, support services, requests and operations across the municipality.", "A unified platform to manage assets, support, requests, and operations across your organization."),
    ("Use your municipal UITOP account to continue.", "Use your organization UITOP account to continue."),
    ("We will email a reset link to your municipal account.", "We will email a reset link to your work account."),
    ("For municipal audits", "For compliance and audits"),
    ("common municipal IT issues", "common workplace IT issues"),
    ("Standard municipal support target", "Standard support target"),
    ("Allowed on municipal endpoints", "Allowed on managed endpoints"),
    ("municipal catalog", "software catalog"),
    ("municipal suite", "standard productivity suite"),
    ("municipal email", "work email"),
    ("municipal staff", "employee"),
    ("Municipal staff", "Employee"),
    ("municipality LAN", "organization LAN"),
    ("municipality network", "organization network"),
    ("municipality-specific", "organization-specific"),
    ("admin@umzinyathi.gov.za", "admin@example.com"),
    ("admin@umzinyathi.gov.za", "{{ default_admin_email }}"),
]

DOC_REPLACEMENTS: list[tuple[str, str]] = [
    ("Umzinyathi IT Operations Platform (UITOP)", "UITOP — Unified IT Operations Platform"),
    ("Umzinyathi IT Operations Platform", "UITOP — Unified IT Operations Platform"),
    ("Umzinyathi Municipality", "your organization"),
    ("Umzinyathi", "your organization"),
    ("admin@umzinyathi.gov.za", "admin@example.com"),
    ("@umzinyathi.gov.za", "@example.com"),
    ("municipal", "organizational"),
    ("Municipal", "Organizational"),
    ("municipality", "organization"),
    ("Municipality", "Organization"),
]

EXTS = {".html", ".css", ".md", ".py", ".ps1", ".bat", ".js"}


def apply_replacements(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if "tools" in parts and path.name == "rebrand_content.py":
        return True
    for s in SKIP:
        if s in str(path):
            return True
    return False


def main() -> None:
    changed = 0
    paths: list[Path] = []
    for d in TARGET_DIRS:
        base = ROOT / d
        if base.is_dir():
            paths.extend(p for p in base.rglob("*") if p.is_file())
    for name in EXTRA_FILES:
        p = ROOT / name
        if p.is_file():
            paths.append(p)

    for path in paths:
        if should_skip(path):
            continue
        if path.suffix.lower() not in {".html", ".css", ".md", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        orig = text
        if "templates" in path.parts or "static" in path.parts:
            text = apply_replacements(text, TEMPLATE_REPLACEMENTS)
        elif path.suffix == ".md" or path.name == "desktop_app.py":
            text = apply_replacements(text, DOC_REPLACEMENTS)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed += 1
            print(path.relative_to(ROOT))
    print(f"Updated {changed} files.")


if __name__ == "__main__":
    main()
