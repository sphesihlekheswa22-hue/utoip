"""Security posture & compliance services for UITOP."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uitop.extensions import db
from uitop.models.inventory import Computer
from uitop.models.security import (
    DeviceSecurityPosture,
    SecurityAuditEvent,
    SecurityIncident,
    SecurityPolicy,
    SecurityThreat,
    SecurityUserActivity,
    SecurityVulnerability,
)
from uitop.models.user import User
from uitop.services.computers_view import relative_time


def utcnow():
    return datetime.now(timezone.utc)


def _calc_compliance(posture: DeviceSecurityPosture, policies: dict[str, SecurityPolicy]) -> int:
    checks = []
    if policies.get("antivirus_required") and policies["antivirus_required"].is_enforced:
        checks.append(bool(posture.antivirus_enabled and posture.antivirus_definitions_ok))
    else:
        checks.append(True)
    if policies.get("firewall_required") and policies["firewall_required"].is_enforced:
        checks.append(bool(posture.firewall_enabled))
    else:
        checks.append(True)
    if policies.get("bitlocker_required") and policies["bitlocker_required"].is_enforced:
        checks.append(bool(posture.bitlocker_enabled))
    else:
        checks.append(True)
    if policies.get("windows_update_required") and policies["windows_update_required"].is_enforced:
        checks.append(bool(posture.windows_updated and posture.pending_updates == 0))
    else:
        checks.append(True)
    if policies.get("usb_storage_blocked") and policies["usb_storage_blocked"].is_enforced:
        checks.append(not posture.usb_storage_allowed)
    else:
        checks.append(True)
    if not checks:
        return 100
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))


def _calc_risk(posture: DeviceSecurityPosture) -> int:
    risk = 0
    if not posture.antivirus_enabled:
        risk += 35
    elif not posture.antivirus_definitions_ok:
        risk += 15
    if not posture.firewall_enabled:
        risk += 30
    if not posture.bitlocker_enabled:
        risk += 10
    if not posture.windows_updated:
        risk += 15
    risk += min(20, (posture.pending_updates or 0) * 3)
    if posture.usb_storage_allowed:
        risk += 5
    return min(100, risk)


def serialize_posture(p: DeviceSecurityPosture) -> dict:
    data = p.to_dict()
    host = p.computer.hostname if p.computer else f"PC-{p.computer_id}"
    data["hostname"] = host
    data["url"] = f"/security/device/{p.computer_id}"
    data["computer_url"] = f"/computers/{p.computer_id}"
    data["last_scan"] = relative_time(p.last_scan_at) if p.last_scan_at else "—"
    data["reported"] = relative_time(p.last_reported_at) if p.last_reported_at else "—"
    data["status_label"] = "Protected" if p.is_protected else "At risk"
    return data


def serialize_threat(t: SecurityThreat) -> dict:
    data = t.to_dict()
    data["severity_label"] = (t.severity or "").title()
    data["status_label"] = (t.status or "").replace("_", " ").title()
    data["detected"] = relative_time(t.detected_at) if t.detected_at else "—"
    data["device"] = t.hostname or (t.computer.hostname if t.computer else "—")
    data["device_url"] = f"/security/device/{t.computer_id}" if t.computer_id else None
    return data


def serialize_vuln(v: SecurityVulnerability) -> dict:
    data = v.to_dict()
    data["severity_label"] = (v.severity or "").title()
    data["status_label"] = (v.status or "").replace("_", " ").title()
    data["detected"] = relative_time(v.detected_at) if v.detected_at else "—"
    data["device"] = v.hostname or (v.computer.hostname if v.computer else "—")
    data["device_url"] = f"/security/device/{v.computer_id}" if v.computer_id else None
    return data


def serialize_incident(i: SecurityIncident) -> dict:
    data = i.to_dict()
    data["severity_label"] = (i.severity or "").title()
    data["status_label"] = (i.status or "").replace("_", " ").title()
    data["type_label"] = (i.incident_type or "").replace("_", " ").title()
    data["detected"] = relative_time(i.detected_at) if i.detected_at else "—"
    data["device"] = i.hostname or (i.computer.hostname if i.computer else "—")
    data["assignee"] = i.assignee.full_name if i.assignee else "Unassigned"
    data["device_url"] = f"/security/device/{i.computer_id}" if i.computer_id else None
    data["ticket_url"] = f"/helpdesk/{i.ticket_id}" if i.ticket_id else None
    return data


def security_kpis() -> dict:
    postures = DeviceSecurityPosture.query.all()
    protected = sum(1 for p in postures if p.is_protected)
    unprotected = sum(1 for p in postures if not p.is_protected)
    avg_compliance = int(round(sum(p.compliance_score for p in postures) / len(postures))) if postures else 100

    threats_open = SecurityThreat.query.filter(SecurityThreat.status.in_(("open", "investigating"))).count()
    critical_threats = SecurityThreat.query.filter(
        SecurityThreat.status.in_(("open", "investigating")),
        SecurityThreat.severity == "critical",
    ).count()
    high_vulns = SecurityVulnerability.query.filter(
        SecurityVulnerability.status == "open",
        SecurityVulnerability.severity.in_(("critical", "high")),
    ).count()
    incidents_open = SecurityIncident.query.filter(
        SecurityIncident.status.in_(("open", "investigating", "contained"))
    ).count()

    day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    failed_today = (
        db.session.query(db.func.coalesce(db.func.sum(SecurityUserActivity.count), 0))
        .filter(
            SecurityUserActivity.activity_type == "failed_login",
            SecurityUserActivity.occurred_at >= day_start,
        )
        .scalar()
        or 0
    )

    # Composite security score
    score = avg_compliance
    score -= min(25, critical_threats * 8 + threats_open * 2)
    score -= min(20, high_vulns * 2)
    score -= min(15, unprotected * 4)
    score -= min(10, incidents_open * 3)
    score = max(0, min(100, int(score)))

    return {
        "security_score": score,
        "critical_threats": critical_threats,
        "high_vulnerabilities": high_vulns,
        "protected_devices": protected,
        "unprotected_devices": unprotected,
        "failed_logins_today": int(failed_today),
        "security_incidents": incidents_open,
        "compliance": avg_compliance,
        "open_threats": threats_open,
        "total_devices": len(postures),
    }


def list_policies() -> list[dict]:
    return [p.to_dict() for p in SecurityPolicy.query.order_by(SecurityPolicy.category, SecurityPolicy.name).all()]


def ai_insights() -> list[dict]:
    insights = []
    # Burst failed logins
    day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    bursts = (
        SecurityUserActivity.query.filter(
            SecurityUserActivity.activity_type == "failed_login",
            SecurityUserActivity.occurred_at >= day_start,
            SecurityUserActivity.count >= 20,
        )
        .order_by(SecurityUserActivity.count.desc())
        .limit(3)
        .all()
    )
    for b in bursts:
        insights.append(
            {
                "title": f"Burst failed logins — {b.username}",
                "body": f"{b.count} failed login attempts on {b.hostname or 'unknown host'}. Recommendation: lock the account and investigate.",
                "tone": "danger",
            }
        )
    # Suspicious PowerShell threats
    ps = SecurityThreat.query.filter(
        SecurityThreat.status == "open",
        SecurityThreat.threat_type == "suspicious_powershell",
    ).count()
    if ps:
        insights.append(
            {
                "title": "Suspicious PowerShell activity",
                "body": f"{ps} open finding(s) for PowerShell from unusual locations — possible malware behavior. Correlate across devices.",
                "tone": "warning",
            }
        )
    # AV disabled
    av_off = DeviceSecurityPosture.query.filter_by(antivirus_enabled=False).count()
    if av_off:
        insights.append(
            {
                "title": "Antivirus disabled",
                "body": f"{av_off} device(s) report antivirus disabled. Enforce policy and open Help Desk tickets.",
                "tone": "danger",
            }
        )
    if not insights:
        insights.append(
            {
                "title": "Posture stable",
                "body": "No high-signal anomalies right now. Keep watching failed logins and unprotected endpoints.",
                "tone": "success",
            }
        )
    return insights


def build_module_payload() -> dict:
    postures = [serialize_posture(p) for p in DeviceSecurityPosture.query.order_by(DeviceSecurityPosture.risk_score.desc()).all()]
    threats = [serialize_threat(t) for t in SecurityThreat.query.order_by(SecurityThreat.detected_at.desc()).limit(100).all()]
    vulns = [serialize_vuln(v) for v in SecurityVulnerability.query.order_by(SecurityVulnerability.detected_at.desc()).limit(100).all()]
    incidents = [
        serialize_incident(i)
        for i in SecurityIncident.query.order_by(SecurityIncident.detected_at.desc()).limit(100).all()
    ]
    user_acts = [
        {
            **a.to_dict(),
            "type_label": (a.activity_type or "").replace("_", " ").title(),
            "when": relative_time(a.occurred_at) if a.occurred_at else "—",
            "severity_label": (a.severity or "").title(),
        }
        for a in SecurityUserActivity.query.order_by(SecurityUserActivity.occurred_at.desc()).limit(80).all()
    ]
    audits = [
        {
            **a.to_dict(),
            "type_label": (a.event_type or "").replace("_", " ").title(),
            "when": a.occurred_at.strftime("%H:%M") if a.occurred_at else "",
            "when_full": relative_time(a.occurred_at) if a.occurred_at else "—",
            "actor": a.actor.full_name if a.actor else "System",
        }
        for a in SecurityAuditEvent.query.order_by(SecurityAuditEvent.occurred_at.desc()).limit(80).all()
    ]
    return {
        "kpis": security_kpis(),
        "devices": postures,
        "threats": threats,
        "vulnerabilities": vulns,
        "incidents": incidents,
        "user_activity": user_acts,
        "policies": list_policies(),
        "audit_events": audits,
        "ai_insights": ai_insights(),
        "antivirus": [d for d in postures],
        "firewall": [d for d in postures],
    }


def build_device_payload(computer_id: int) -> dict | None:
    computer = Computer.query.get(computer_id)
    if not computer:
        return None
    posture = DeviceSecurityPosture.query.filter_by(computer_id=computer_id).first()
    if not posture:
        # Lazy default posture for inventory computers without seed row
        posture = DeviceSecurityPosture(
            computer_id=computer_id,
            antivirus_name="Microsoft Defender",
            antivirus_enabled=True,
            antivirus_definitions_ok=True,
            last_scan_at=utcnow() - timedelta(hours=6),
            firewall_enabled=True,
            bitlocker_enabled=False,
            windows_updated=True,
            pending_updates=0,
            usb_storage_allowed=True,
            compliance_score=80,
            risk_score=15,
            last_reported_at=utcnow(),
        )
        db.session.add(posture)
        db.session.commit()

    policies = {p.key: p for p in SecurityPolicy.query.all()}
    checks = [
        {"name": "BitLocker", "ok": posture.bitlocker_enabled, "detail": "Enabled" if posture.bitlocker_enabled else "Disabled"},
        {"name": "Windows Updated", "ok": posture.windows_updated and posture.pending_updates == 0, "detail": f"{posture.pending_updates} pending" if posture.pending_updates else "Current"},
        {"name": "Antivirus", "ok": posture.antivirus_enabled and posture.antivirus_definitions_ok, "detail": posture.antivirus_name or "—"},
        {"name": "Firewall", "ok": posture.firewall_enabled, "detail": "Enabled" if posture.firewall_enabled else "Disabled"},
        {"name": "USB Storage", "ok": (not posture.usb_storage_allowed) if policies.get("usb_storage_blocked") and policies["usb_storage_blocked"].is_enforced else True, "detail": "Blocked" if not posture.usb_storage_allowed else "Allowed"},
        {"name": "Password Policy", "ok": True, "detail": policies.get("password_min_length").value + " chars" if policies.get("password_min_length") else "Org policy"},
    ]
    events = [
        {
            **a.to_dict(),
            "when": relative_time(a.occurred_at) if a.occurred_at else "—",
            "type_label": (a.event_type or "").replace("_", " ").title(),
        }
        for a in SecurityAuditEvent.query.filter_by(computer_id=computer_id)
        .order_by(SecurityAuditEvent.occurred_at.desc())
        .limit(30)
        .all()
    ]
    return {
        "device": {
            "id": computer.id,
            "hostname": computer.hostname,
            "ip": computer.ip_address,
            "os": computer.os_name,
            "status": (computer.status or "unknown").title(),
            "url": f"/computers/{computer.id}",
        },
        "posture": serialize_posture(posture),
        "checks": checks,
        "threats": [
            serialize_threat(t)
            for t in SecurityThreat.query.filter_by(computer_id=computer_id).order_by(SecurityThreat.detected_at.desc()).all()
        ],
        "vulnerabilities": [
            serialize_vuln(v)
            for v in SecurityVulnerability.query.filter_by(computer_id=computer_id)
            .order_by(SecurityVulnerability.detected_at.desc())
            .all()
        ],
        "incidents": [
            serialize_incident(i)
            for i in SecurityIncident.query.filter_by(computer_id=computer_id)
            .order_by(SecurityIncident.detected_at.desc())
            .all()
        ],
        "events": events,
    }


def next_incident_number() -> str:
    last = SecurityIncident.query.order_by(SecurityIncident.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"SI-{1000 + n}"


def update_incident_status(incident_id: int, status: str) -> SecurityIncident | None:
    row = SecurityIncident.query.get(incident_id)
    if not row:
        return None
    row.status = status
    row.updated_at = utcnow()
    if status in ("resolved", "closed") and not row.resolved_at:
        row.resolved_at = utcnow()
    db.session.add(
        SecurityAuditEvent(
            event_type="incident_status",
            message=f"Incident {row.incident_number} → {status}",
            severity="info",
            computer_id=row.computer_id,
            hostname=row.hostname,
            occurred_at=utcnow(),
        )
    )
    db.session.commit()
    return row


def update_threat_status(threat_id: int, status: str) -> SecurityThreat | None:
    row = SecurityThreat.query.get(threat_id)
    if not row:
        return None
    row.status = status
    db.session.commit()
    return row


def seed_security_demo(*, actor_id: int | None = None) -> int:
    if DeviceSecurityPosture.query.count():
        return 0

    computers = Computer.query.order_by(Computer.id).all()
    if not computers:
        return 0
    admin = User.query.filter_by(id=actor_id).first() if actor_id else User.query.order_by(User.id).first()
    actor_id = admin.id if admin else None

    # Policies
    policy_defs = [
        ("password_min_length", "Password minimum length", "12", "identity", "Minimum 12 characters for user passwords."),
        ("bitlocker_required", "BitLocker required", "required", "endpoint", "Full disk encryption required on corporate endpoints."),
        ("firewall_required", "Firewall always enabled", "enabled", "endpoint", "Windows Firewall must remain enabled."),
        ("antivirus_required", "Antivirus required", "enabled", "endpoint", "Microsoft Defender or approved AV must be active."),
        ("usb_storage_blocked", "USB storage blocked", "blocked", "endpoint", "Removable USB storage blocked by policy."),
        ("windows_update_required", "Windows Update current", "required", "endpoint", "Devices must apply security updates promptly."),
    ]
    policies: dict[str, SecurityPolicy] = {}
    for key, name, value, cat, desc in policy_defs:
        p = SecurityPolicy(key=key, name=name, value=value, category=cat, description=desc, is_enforced=True)
        db.session.add(p)
        policies[key] = p
    db.session.flush()

    # Device postures — most healthy, a few at risk
    created = 0
    for idx, c in enumerate(computers):
        at_risk = idx % 5 == 0
        av_off = idx == 0
        fw_off = idx == 1
        posture = DeviceSecurityPosture(
            computer_id=c.id,
            antivirus_name="Microsoft Defender",
            antivirus_enabled=not av_off,
            antivirus_definitions_ok=not av_off,
            last_scan_at=utcnow() - timedelta(hours=(2 if not at_risk else 72)),
            firewall_enabled=not fw_off,
            bitlocker_enabled=idx % 3 != 0,
            windows_updated=idx % 4 != 0,
            pending_updates=0 if idx % 4 != 0 else (3 + idx % 5),
            usb_storage_allowed=idx % 2 == 0,
            last_reported_at=utcnow() - timedelta(minutes=15 + idx),
        )
        posture.compliance_score = _calc_compliance(posture, policies)
        posture.risk_score = _calc_risk(posture)
        db.session.add(posture)
        created += 1

    c0 = computers[0]
    c1 = computers[1] if len(computers) > 1 else c0
    c2 = computers[2] if len(computers) > 2 else c0

    threats = [
        SecurityThreat(
            title="Suspicious PowerShell",
            description="Encoded PowerShell executed from %TEMP% — unusual for this user profile.",
            threat_type="suspicious_powershell",
            severity="high",
            status="open",
            computer_id=c0.id,
            hostname=c0.hostname,
            detected_at=utcnow() - timedelta(hours=2),
        ),
        SecurityThreat(
            title="Firewall disabled",
            description="Windows Firewall reported disabled by agent.",
            threat_type="firewall_disabled",
            severity="critical",
            status="open",
            computer_id=c1.id,
            hostname=c1.hostname,
            detected_at=utcnow() - timedelta(hours=1),
        ),
        SecurityThreat(
            title="Unauthorized software detected",
            description="Remote access tool installed outside approved software catalog.",
            threat_type="unauthorized_software",
            severity="medium",
            status="investigating",
            computer_id=c2.id,
            hostname=c2.hostname,
            detected_at=utcnow() - timedelta(days=1),
        ),
    ]
    for t in threats:
        db.session.add(t)

    vulns = [
        SecurityVulnerability(
            title="Windows Update Missing",
            description="Cumulative security update pending for more than 14 days.",
            category="update",
            severity="high",
            status="open",
            computer_id=c0.id,
            hostname=c0.hostname,
            detected_at=utcnow() - timedelta(days=2),
        ),
        SecurityVulnerability(
            title="Chrome Outdated",
            description="Browser version behind current stable channel.",
            category="software",
            severity="medium",
            status="open",
            computer_id=c0.id,
            hostname=c0.hostname,
            detected_at=utcnow() - timedelta(days=1),
        ),
        SecurityVulnerability(
            title="SMBv1 Enabled",
            description="Legacy SMBv1 protocol enabled — high ransomware risk.",
            category="config",
            severity="critical",
            status="open",
            computer_id=c1.id,
            hostname=c1.hostname,
            cve_id="CVE-2017-0144",
            detected_at=utcnow() - timedelta(hours=8),
        ),
        SecurityVulnerability(
            title="Office macro security weak",
            description="Macros enabled for all documents.",
            category="config",
            severity="high",
            status="open",
            computer_id=c2.id,
            hostname=c2.hostname,
            detected_at=utcnow() - timedelta(days=3),
        ),
    ]
    for v in vulns:
        db.session.add(v)

    incidents = [
        SecurityIncident(
            incident_number=next_incident_number(),
            title="Firewall Disabled",
            description="Critical control disabled on endpoint — investigate and re-enable.",
            incident_type="firewall_disabled",
            severity="critical",
            status="open",
            computer_id=c1.id,
            hostname=c1.hostname,
            assignee_user_id=actor_id,
            detected_at=utcnow() - timedelta(hours=1),
        ),
        SecurityIncident(
            incident_number=f"SI-{1002}",
            title="Multiple Failed Logins",
            description="Burst failed authentications may indicate credential stuffing.",
            incident_type="failed_logins",
            severity="high",
            status="investigating",
            computer_id=c0.id,
            hostname=c0.hostname,
            assignee_user_id=actor_id,
            detected_at=utcnow() - timedelta(hours=3),
        ),
        SecurityIncident(
            incident_number=f"SI-{1003}",
            title="USB Storage Enabled",
            description="Removable storage allowed contrary to endpoint policy.",
            incident_type="usb_storage",
            severity="medium",
            status="open",
            computer_id=c2.id,
            hostname=c2.hostname,
            detected_at=utcnow() - timedelta(days=1),
        ),
        SecurityIncident(
            incident_number=f"SI-{1004}",
            title="Unauthorized Software",
            description="Unapproved remote tool installed.",
            incident_type="unauthorized_software",
            severity="high",
            status="contained",
            computer_id=c2.id,
            hostname=c2.hostname,
            detected_at=utcnow() - timedelta(days=2),
        ),
    ]
    # Fix incident numbers after flush pattern
    for i, inc in enumerate(incidents):
        inc.incident_number = f"SI-{1001 + i}"
        db.session.add(inc)

    users = User.query.filter_by(is_active=True).order_by(User.id).limit(5).all()
    u0 = users[0] if users else None
    activities = [
        SecurityUserActivity(
            activity_type="failed_login",
            username=u0.full_name if u0 else "John Smith",
            user_id=u0.id if u0 else None,
            computer_id=c0.id,
            hostname=c0.hostname,
            count=45,
            severity="critical",
            message="45 failed login attempts within 10 minutes.",
            occurred_at=utcnow() - timedelta(minutes=25),
        ),
        SecurityUserActivity(
            activity_type="failed_login",
            username="finance.clerk",
            computer_id=c1.id,
            hostname=c1.hostname,
            count=12,
            severity="high",
            message="12 failed logins today.",
            occurred_at=utcnow() - timedelta(hours=2),
        ),
        SecurityUserActivity(
            activity_type="account_lockout",
            username="finance.clerk",
            computer_id=c1.id,
            hostname=c1.hostname,
            count=1,
            severity="medium",
            message="Account locked after repeated failures.",
            occurred_at=utcnow() - timedelta(hours=1, minutes=50),
        ),
        SecurityUserActivity(
            activity_type="password_reset",
            username=u0.full_name if u0 else "Admin",
            user_id=u0.id if u0 else None,
            count=1,
            severity="info",
            message="Password reset completed.",
            occurred_at=utcnow() - timedelta(hours=5),
        ),
        SecurityUserActivity(
            activity_type="new_admin_account",
            username="temp.admin",
            count=1,
            severity="high",
            message="New local administrator account created.",
            computer_id=c2.id,
            hostname=c2.hostname,
            occurred_at=utcnow() - timedelta(days=1),
        ),
    ]
    for a in activities:
        db.session.add(a)

    audits = [
        SecurityAuditEvent(
            event_type="firewall_disabled",
            message="Firewall Disabled",
            severity="critical",
            computer_id=c1.id,
            hostname=c1.hostname,
            occurred_at=utcnow() - timedelta(hours=1, minutes=50),
        ),
        SecurityAuditEvent(
            event_type="admin_login",
            message="Administrator Login",
            severity="info",
            computer_id=c0.id,
            hostname=c0.hostname,
            actor_user_id=actor_id,
            occurred_at=utcnow() - timedelta(hours=1, minutes=48),
        ),
        SecurityAuditEvent(
            event_type="usb_connected",
            message="USB Device Connected",
            severity="warning",
            computer_id=c2.id,
            hostname=c2.hostname,
            occurred_at=utcnow() - timedelta(hours=1, minutes=40),
        ),
        SecurityAuditEvent(
            event_type="policy_updated",
            message="Policy Updated — USB storage blocked",
            severity="info",
            actor_user_id=actor_id,
            occurred_at=utcnow() - timedelta(hours=1, minutes=30),
        ),
        SecurityAuditEvent(
            event_type="antivirus_disabled",
            message="Antivirus Disabled",
            severity="critical",
            computer_id=c0.id,
            hostname=c0.hostname,
            occurred_at=utcnow() - timedelta(hours=3),
        ),
    ]
    for a in audits:
        db.session.add(a)

    db.session.commit()
    return created
