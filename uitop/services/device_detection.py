"""Detect and claim real employee workstations from agent inventory / network."""
from __future__ import annotations

import getpass
import re
import socket
from datetime import datetime, timedelta, timezone

from uitop.extensions import db
from uitop.models.assets import Asset, AssetAssignment
from uitop.models.inventory import Computer, Printer
from uitop.models.user import User


def utcnow():
    return datetime.now(timezone.utc)


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_seed_or_fake_computer(computer: Computer) -> bool:
    """Exclude demo/seed inventory from employee My Devices."""
    agent = (computer.agent_id or "").lower()
    host = (computer.hostname or "").lower()
    if agent.startswith("seed-"):
        return True
    fake_prefixes = (
        "pc-fin-",
        "pc-it-",
        "lap-corp-",
        "pc-demo-",
        "pc-agent-test",
        "smoke-pc",
        "test-pc",
    )
    if any(host.startswith(p) for p in fake_prefixes):
        return True
    # Network-scan placeholder hosts without an agent are not "my device"
    if host.startswith("host-") and not computer.agent_id:
        return True
    return False


def is_real_agent_computer(computer: Computer) -> bool:
    if computer is None or is_seed_or_fake_computer(computer):
        return False
    if not computer.agent_id:
        return False
    return True


def _normalize_login(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    # DOMAIN\user or user@domain
    if "\\" in raw:
        raw = raw.split("\\")[-1]
    if "@" in raw:
        raw = raw.split("@")[0]
    return re.sub(r"[^a-z0-9._-]", "", raw)


def user_login_aliases(user: User) -> set[str]:
    aliases: set[str] = set()
    email_local = _normalize_login((user.email or "").split("@")[0])
    if email_local:
        aliases.add(email_local)
        # sarah.finance -> sarah
        if "." in email_local:
            aliases.add(email_local.split(".")[0])
    name = (user.full_name or "").strip().lower()
    if name:
        parts = [p for p in re.split(r"\s+", name) if p]
        if parts:
            aliases.add(_normalize_login(parts[0]))
            aliases.add(_normalize_login("".join(parts)))
            if len(parts) >= 2:
                aliases.add(_normalize_login(parts[0] + parts[-1]))
    return {a for a in aliases if a and len(a) >= 2}


def inventory_login(computer: Computer) -> str:
    payload = computer.inventory_payload if isinstance(computer.inventory_payload, dict) else {}
    for key in ("logged_in_user", "windows_user", "username", "user", "current_user"):
        val = payload.get(key)
        if val:
            return _normalize_login(str(val))
    return ""


def computer_matches_user_login(computer: Computer, user: User) -> bool:
    login = inventory_login(computer)
    if not login:
        return False
    aliases = user_login_aliases(user)
    return login in aliases


def find_computers_by_client_ip(remote_addr: str | None) -> list[Computer]:
    ip = (remote_addr or "").strip()
    if not ip or ip in {"127.0.0.1", "::1", "localhost"}:
        return []
    rows = (
        Computer.query.filter(Computer.ip_address == ip)
        .order_by(Computer.last_seen_at.desc())
        .all()
    )
    return _newest_per_hostname([c for c in rows if is_real_agent_computer(c)])


def find_server_local_computers() -> list[Computer]:
    """When UITOP runs on the employee PC, match this machine's hostname."""
    try:
        host = socket.gethostname()
    except OSError:
        return []
    if not host:
        return []
    rows = (
        Computer.query.filter(Computer.hostname.ilike(host))
        .order_by(Computer.last_seen_at.desc())
        .all()
    )
    real = [c for c in rows if is_real_agent_computer(c)]
    return _newest_per_hostname(real)


def _newest_per_hostname(computers: list[Computer]) -> list[Computer]:
    best: dict[str, Computer] = {}
    for c in computers:
        key = (c.hostname or "").strip().lower() or f"id:{c.id}"
        prev = best.get(key)
        if prev is None:
            best[key] = c
            continue
        prev_seen = _as_utc(prev.last_seen_at) or datetime.min.replace(tzinfo=timezone.utc)
        cur_seen = _as_utc(c.last_seen_at) or datetime.min.replace(tzinfo=timezone.utc)
        if cur_seen >= prev_seen:
            best[key] = c
    return list(best.values())


def find_computers_by_user_login(user: User) -> list[Computer]:
    matches = []
    for computer in Computer.query.filter(Computer.agent_id.isnot(None)).all():
        if not is_real_agent_computer(computer):
            continue
        if computer_matches_user_login(computer, user):
            matches.append(computer)
    matches.sort(key=lambda c: _as_utc(c.last_seen_at) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return _newest_per_hostname(matches)


def ensure_user_owns_computer(user: User, computer: Computer, *, source: str) -> Asset | None:
    """Assign/link a detected computer to the employee (idempotent)."""
    from uitop.services.assets import assign_asset, ensure_asset_for_computer

    if not is_real_agent_computer(computer):
        return None

    asset = ensure_asset_for_computer(computer)
    asset.custodian_user_id = user.id
    if user.department_id:
        asset.department_id = user.department_id
    asset.status = "in_use"

    open_for_user = AssetAssignment.query.filter_by(
        asset_id=asset.id, user_id=user.id, returned_at=None
    ).first()
    if open_for_user is None:
        # Soft-claim without stealing other active users' open rows when recently claimed by someone else
        other = (
            AssetAssignment.query.filter_by(asset_id=asset.id, returned_at=None)
            .filter(AssetAssignment.user_id != user.id)
            .first()
        )
        if other is None:
            assign_asset(
                asset.id,
                assignee_name=user.full_name,
                user_id=user.id,
                department_id=user.department_id,
                notes=f"Auto-detected ({source})",
                actor_id=user.id,
            )
        else:
            # Still show via custodian
            db.session.flush()
    else:
        db.session.flush()
    return asset


def detect_and_claim_for_user(user: User, *, remote_addr: str | None = None) -> list[dict]:
    """Find real workstations for this employee and claim them."""
    found: dict[int, tuple[Computer, str]] = {}

    for c in find_computers_by_user_login(user):
        found[c.id] = (c, "agent login")
    for c in find_computers_by_client_ip(remote_addr):
        found[c.id] = (c, "network IP")
    # UITOP running on this workstation (desktop install / local browser)
    for c in find_server_local_computers():
        found.setdefault(c.id, (c, "this PC"))

    claimed = []
    for computer, source in found.values():
        asset = ensure_user_owns_computer(user, computer, source=source)
        claimed.append({"computer": computer, "source": source, "asset": asset})
    if claimed:
        db.session.commit()
    return claimed


def serialize_detected_computer(computer: Computer, *, source: str | None = None) -> dict:
    from uitop.services.computers_view import serialize_computer

    row = serialize_computer(computer)
    row["detection_source"] = source
    row["is_agent"] = bool(computer.agent_id)
    row["logged_in_user"] = inventory_login(computer) or None
    row["ip_address"] = computer.ip_address
    return row


def real_office_printers(user: User, computers: list[Computer]) -> list[dict]:
    """Printers near the employee (same /24 as their PC) or department — no demo filler."""
    from uitop.services.inventory_view import serialize_printer

    printers: dict[int, Printer] = {}
    if user.department_id:
        for p in Printer.query.filter_by(department_id=user.department_id).all():
            printers[p.id] = p

    subnets: set[str] = set()
    for c in computers:
        ip = (c.ip_address or "").strip()
        parts = ip.split(".")
        if len(parts) == 4:
            subnets.add(".".join(parts[:3]) + ".")

    if subnets:
        for p in Printer.query.filter(Printer.ip_address.isnot(None)).all():
            pip = p.ip_address or ""
            if any(pip.startswith(s) for s in subnets):
                printers[p.id] = p

    # Prefer printers that have been seen / SNMP'd / discovered recently
    cutoff = utcnow() - timedelta(days=30)
    rows = []
    for p in printers.values():
        name = (p.name or "").upper()
        if name.startswith("PRT-FIN-") or name.startswith("PRT-CORP-"):
            # Keep only if recently seen (real telemetry); skip stale seed-only
            last = _as_utc(p.last_seen_at) or _as_utc(getattr(p, "last_snmp_at", None))
            if last is None or last < cutoff:
                continue
        rows.append(serialize_printer(p))
    rows.sort(key=lambda r: (r.get("name") or "").lower())
    return rows


def current_os_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return ""
