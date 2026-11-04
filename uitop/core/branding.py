"""Universal UITOP branding — organisation-agnostic defaults (override via env & Settings)."""
from __future__ import annotations

import os

APP_SHORT_NAME = "UITOP"
APP_TAGLINE = "Unified IT Operations Platform"
APP_TITLE = f"{APP_SHORT_NAME} — {APP_TAGLINE}"
APP_DESCRIPTION = (
    "Manage infrastructure, assets, support, security, and monitoring from one workplace IT platform."
)

DEFAULT_DEMO_ORG_NAME = "Demo Organization"
DEFAULT_EMAIL_DOMAIN = "example.com"
DEFAULT_ADMIN_LOCAL = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@UITOP2026"


def org_name_from_env() -> str:
    return (os.getenv("ORG_NAME") or DEFAULT_DEMO_ORG_NAME).strip() or DEFAULT_DEMO_ORG_NAME


def email_domain_from_env() -> str:
    domain = (os.getenv("ORG_EMAIL_DOMAIN") or DEFAULT_EMAIL_DOMAIN).strip().lstrip("@")
    return domain or DEFAULT_EMAIL_DOMAIN


def admin_email_from_env() -> str:
    explicit = (os.getenv("UITOP_ADMIN_EMAIL") or "").strip().lower()
    if explicit:
        return explicit
    return f"{DEFAULT_ADMIN_LOCAL}@{email_domain_from_env()}"


def org_email(local_part: str) -> str:
    local = (local_part or "user").strip().lower().replace(" ", ".")
    return f"{local}@{email_domain_from_env()}"


def resolve_branding(general_settings: dict | None = None) -> dict[str, str]:
    """Merge env defaults with Settings → General (when available)."""
    general = general_settings or {}
    org_name = (general.get("org_name") or "").strip() or org_name_from_env()
    tagline = (general.get("org_tagline") or "").strip() or APP_TAGLINE
    domain = (general.get("org_email_domain") or "").strip().lstrip("@") or email_domain_from_env()
    subtitle = (general.get("org_portal_subtitle") or "").strip() or "People · Technology · Service Delivery"
    footer = (general.get("org_footer_line") or "").strip() or f"{org_name} · IT Operations"
    admin_email = admin_email_from_env()
    if general.get("org_email_domain"):
        admin_local = (os.getenv("UITOP_ADMIN_LOCAL") or DEFAULT_ADMIN_LOCAL).strip()
        if not os.getenv("UITOP_ADMIN_EMAIL"):
            admin_email = f"{admin_local}@{domain}"
    return {
        "app_name": APP_SHORT_NAME,
        "app_tagline": tagline,
        "app_title": f"{APP_SHORT_NAME} — {tagline}",
        "app_description": APP_DESCRIPTION,
        "org_name": org_name,
        "org_email_domain": domain,
        "org_portal_subtitle": subtitle,
        "org_footer_line": footer,
        "default_admin_email": admin_email,
    }
