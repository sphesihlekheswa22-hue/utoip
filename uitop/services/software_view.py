"""Software Management — mock enterprise data for UI (agent sync later)."""
from __future__ import annotations


def kpis() -> dict:
    return {
        "titles": 245,
        "installs": 8542,
        "approved": 180,
        "unauthorized": 12,
        "outdated": 37,
        "expiring_licenses": 8,
    }


def catalog() -> list[dict]:
    return [
        {
            "id": 1,
            "name": "Google Chrome",
            "vendor": "Google",
            "version": "139.0.7258.128",
            "latest_version": "139.0.7258.128",
            "category": "Browser",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "98 MB",
            "security_risk": "Low",
            "security_score": 92,
            "installed_count": 412,
            "license": None,
        },
        {
            "id": 2,
            "name": "Microsoft 365 Apps",
            "vendor": "Microsoft",
            "version": "2406",
            "latest_version": "2406",
            "category": "Productivity",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "3.2 GB",
            "security_risk": "Low",
            "security_score": 94,
            "installed_count": 231,
            "license": {"purchased": 250, "installed": 231, "remaining": 19, "expires": "2027-03-31"},
        },
        {
            "id": 3,
            "name": "VLC media player",
            "vendor": "VideoLAN",
            "version": "3.0.21",
            "latest_version": "4.0.0-rc1",
            "category": "Media",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "42 MB",
            "security_risk": "Low",
            "security_score": 88,
            "installed_count": 86,
            "license": None,
        },
        {
            "id": 4,
            "name": "Adobe Acrobat Pro",
            "vendor": "Adobe",
            "version": "24.003.20112",
            "latest_version": "24.003.20112",
            "category": "Productivity",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "512 MB",
            "security_risk": "Medium",
            "security_score": 78,
            "installed_count": 67,
            "license": {"purchased": 50, "installed": 67, "remaining": -17, "expires": "2026-11-15", "over": True},
        },
        {
            "id": 5,
            "name": "uTorrent",
            "vendor": "BitTorrent",
            "version": "3.6.0",
            "latest_version": "3.6.0",
            "category": "P2P",
            "approved": False,
            "deployable": False,
            "archived": False,
            "installer_size": "2.4 MB",
            "security_risk": "High",
            "security_score": 28,
            "installed_count": 4,
            "license": None,
            "blacklisted": True,
        },
        {
            "id": 6,
            "name": "Git",
            "vendor": "Software Freedom Conservancy",
            "version": "2.45.2",
            "latest_version": "2.46.0",
            "category": "Developer",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "58 MB",
            "security_risk": "Low",
            "security_score": 90,
            "installed_count": 54,
            "license": None,
        },
        {
            "id": 7,
            "name": "Docker Desktop",
            "vendor": "Docker Inc.",
            "version": "4.33.0",
            "latest_version": "4.34.1",
            "category": "Developer",
            "approved": True,
            "deployable": False,
            "archived": False,
            "installer_size": "580 MB",
            "security_risk": "Medium",
            "security_score": 74,
            "installed_count": 18,
            "license": {"purchased": 25, "installed": 18, "remaining": 7, "expires": "2026-09-01"},
        },
        {
            "id": 8,
            "name": "Zoom Workplace",
            "vendor": "Zoom",
            "version": "6.1.10",
            "latest_version": "6.1.12",
            "category": "Collaboration",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "120 MB",
            "security_risk": "Low",
            "security_score": 85,
            "installed_count": 198,
            "license": None,
        },
        {
            "id": 9,
            "name": "AutoCAD",
            "vendor": "Autodesk",
            "version": "2025",
            "latest_version": "2025",
            "category": "Engineering",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "4.1 GB",
            "security_risk": "Low",
            "security_score": 86,
            "installed_count": 22,
            "license": {"purchased": 30, "installed": 22, "remaining": 8, "expires": "2026-12-31"},
        },
        {
            "id": 10,
            "name": "Python",
            "vendor": "Python Software Foundation",
            "version": "3.12.4",
            "latest_version": "3.12.5",
            "category": "Developer",
            "approved": True,
            "deployable": True,
            "archived": False,
            "installer_size": "28 MB",
            "security_risk": "Low",
            "security_score": 91,
            "installed_count": 41,
            "license": None,
        },
    ]


def computers_with_software() -> list[dict]:
    """Installed software inventory — agent-sourced (mock)."""
    return [
        {
            "computer_id": 1,
            "hostname": "PC-001",
            "user": "K. Zulu",
            "department": "Finance",
            "apps": [
                {"software_id": 1, "name": "Google Chrome", "version": "135.0.7049.95", "install_date": "2025-11-02", "status": "Outdated"},
                {"software_id": 2, "name": "Microsoft 365 Apps", "version": "2406", "install_date": "2025-08-14", "status": "Current"},
                {"software_id": 8, "name": "Zoom Workplace", "version": "6.1.10", "install_date": "2026-01-20", "status": "Update available"},
                {"software_id": 4, "name": "Adobe Acrobat Pro", "version": "24.003.20112", "install_date": "2025-09-01", "status": "Current"},
            ],
        },
        {
            "computer_id": 2,
            "hostname": "PC-014",
            "user": "L. Mokoena",
            "department": "Corporate Services",
            "apps": [
                {"software_id": 1, "name": "Google Chrome", "version": "139.0.7258.128", "install_date": "2026-07-01", "status": "Current"},
                {"software_id": 2, "name": "Microsoft 365 Apps", "version": "2406", "install_date": "2025-08-14", "status": "Current"},
                {"software_id": 3, "name": "VLC media player", "version": "3.0.20", "install_date": "2024-06-11", "status": "Outdated"},
                {"software_id": 10, "name": "Python", "version": "3.12.4", "install_date": "2026-03-08", "status": "Update available"},
            ],
        },
        {
            "computer_id": 3,
            "hostname": "PC-020",
            "user": "S. Dlamini",
            "department": "IT Operations",
            "apps": [
                {"software_id": 1, "name": "Google Chrome", "version": "139.0.7258.128", "install_date": "2026-07-10", "status": "Current"},
                {"software_id": 6, "name": "Git", "version": "2.45.2", "install_date": "2026-02-01", "status": "Update available"},
                {"software_id": 7, "name": "Docker Desktop", "version": "4.33.0", "install_date": "2026-04-12", "status": "Update available"},
                {"software_id": 10, "name": "Python", "version": "3.12.4", "install_date": "2026-02-01", "status": "Update available"},
                {"software_id": 2, "name": "Microsoft 365 Apps", "version": "2406", "install_date": "2025-08-14", "status": "Current"},
            ],
        },
        {
            "computer_id": 4,
            "hostname": "PC-108",
            "user": "J. Botha",
            "department": "Technical Services",
            "apps": [
                {"software_id": 1, "name": "Google Chrome", "version": "139.0.7258.128", "install_date": "2026-06-22", "status": "Current"},
                {"software_id": 9, "name": "AutoCAD", "version": "2025", "install_date": "2025-12-05", "status": "Current"},
                {"software_id": 2, "name": "Microsoft 365 Apps", "version": "2406", "install_date": "2025-08-14", "status": "Current"},
                {"software_id": 5, "name": "uTorrent", "version": "3.6.0", "install_date": "2026-05-18", "status": "Unauthorized"},
            ],
        },
        {
            "computer_id": 5,
            "hostname": "Sphesihle",
            "user": "IT Admin",
            "department": "IT Operations",
            "apps": [
                {"software_id": 1, "name": "Google Chrome", "version": "139.0.7258.128", "install_date": "2026-07-15", "status": "Current"},
                {"software_id": 6, "name": "Git", "version": "2.45.2", "install_date": "2026-01-10", "status": "Update available"},
                {"software_id": 7, "name": "Docker Desktop", "version": "4.33.0", "install_date": "2026-03-01", "status": "Update available"},
                {"software_id": 10, "name": "Python", "version": "3.12.4", "install_date": "2026-01-10", "status": "Update available"},
            ],
        },
    ]


def deployments() -> list[dict]:
    return [
        {
            "id": 101,
            "software_id": 1,
            "software": "Google Chrome",
            "version": "139.0.7258.128",
            "target": "Finance Department",
            "computers": 20,
            "success": 18,
            "failed": 1,
            "pending": 1,
            "status": "In progress",
            "started": "Today 09:14",
            "progress": 90,
        },
        {
            "id": 102,
            "software_id": 8,
            "software": "Zoom Workplace",
            "version": "6.1.12",
            "target": "Corporate Services",
            "computers": 45,
            "success": 45,
            "failed": 0,
            "pending": 0,
            "status": "Completed",
            "started": "Yesterday 14:02",
            "progress": 100,
        },
        {
            "id": 103,
            "software_id": 9,
            "software": "AutoCAD",
            "version": "2025",
            "target": "Engineering · 8 devices",
            "computers": 8,
            "success": 0,
            "failed": 0,
            "pending": 8,
            "status": "Queued",
            "started": "Scheduled tomorrow 06:00",
            "progress": 0,
        },
    ]


def updates() -> list[dict]:
    return [
        {
            "software_id": 1,
            "name": "Google Chrome",
            "current": "139.0.7258.128",
            "installed_typical": "135.0.7049.95",
            "affected": 47,
            "status": "Update available",
            "severity": "medium",
        },
        {
            "software_id": 8,
            "name": "Zoom Workplace",
            "current": "6.1.12",
            "installed_typical": "6.1.10",
            "affected": 63,
            "status": "Update available",
            "severity": "low",
        },
        {
            "software_id": 6,
            "name": "Git",
            "current": "2.46.0",
            "installed_typical": "2.45.2",
            "affected": 32,
            "status": "Update available",
            "severity": "low",
        },
        {
            "software_id": 7,
            "name": "Docker Desktop",
            "current": "4.34.1",
            "installed_typical": "4.33.0",
            "affected": 12,
            "status": "Update available",
            "severity": "medium",
        },
        {
            "software_id": 3,
            "name": "VLC media player",
            "current": "4.0.0-rc1",
            "installed_typical": "3.0.20",
            "affected": 41,
            "status": "Update available",
            "severity": "low",
        },
    ]


def requests() -> list[dict]:
    return [
        {
            "id": 501,
            "software": "AutoCAD",
            "software_id": 9,
            "requester": "N. Naidoo",
            "department": "Engineering",
            "justification": "New draughtsperson starting Monday — needs licensed seat.",
            "status": "Pending",
            "requested": "2 hours ago",
        },
        {
            "id": 502,
            "software": "Adobe Acrobat Pro",
            "software_id": 4,
            "requester": "Finance Desk",
            "department": "Finance",
            "justification": "PDF form signing for SCM tenders.",
            "status": "Pending",
            "requested": "Yesterday",
        },
        {
            "id": 503,
            "software": "Visual Studio Code",
            "software_id": None,
            "requester": "S. Dlamini",
            "department": "IT Operations",
            "justification": "Standard IDE for municipal scripts — not yet in catalog.",
            "status": "Approved",
            "requested": "3 days ago",
        },
        {
            "id": 504,
            "software": "Slack",
            "software_id": None,
            "requester": "Marketing intern",
            "department": "Corporate Services",
            "justification": "Team chat with agency.",
            "status": "Denied",
            "requested": "Last week",
        },
    ]


def blacklist() -> list[dict]:
    return [
        {
            "software_id": 5,
            "name": "uTorrent",
            "vendor": "BitTorrent",
            "reason": "Unauthorized P2P — data exfiltration risk",
            "action": "Alert + quarantine",
            "detections": 4,
            "auto_remove": True,
        },
        {
            "id": "bl-2",
            "software_id": None,
            "name": "AnyDesk (unmanaged)",
            "vendor": "AnyDesk Software",
            "reason": "Remote access outside approved RMM",
            "action": "Alert only",
            "detections": 2,
            "auto_remove": False,
        },
        {
            "id": "bl-3",
            "software_id": None,
            "name": "CCleaner",
            "vendor": "Piriform",
            "reason": "Known adware bundles in free builds",
            "action": "Alert + block install",
            "detections": 1,
            "auto_remove": False,
        },
    ]


def license_rows() -> list[dict]:
    """Software-tab view; license_id links into Licenses module when known."""
    # software_id -> licenses module id
    link = {2: 1, 4: 2, 9: 3, 7: 4, 8: 7}
    rows = []
    for s in catalog():
        if s.get("license"):
            lic = s["license"]
            rows.append(
                {
                    "software_id": s["id"],
                    "license_id": link.get(s["id"]),
                    "name": s["name"],
                    "vendor": s["vendor"],
                    "purchased": lic["purchased"],
                    "installed": lic["installed"],
                    "remaining": lic["remaining"],
                    "expires": lic["expires"],
                    "over": lic.get("over", False) or lic["remaining"] < 0,
                    "expiring_soon": lic["expires"].startswith("2026-09") or lic["expires"].startswith("2026-11"),
                }
            )
    return rows


def installations_for(software_id: int) -> list[dict]:
    rows = []
    for pc in computers_with_software():
        for app in pc["apps"]:
            if app["software_id"] == software_id:
                rows.append(
                    {
                        "computer_id": pc["computer_id"],
                        "hostname": pc["hostname"],
                        "user": pc["user"],
                        "department": pc["department"],
                        "version": app["version"],
                        "install_date": app["install_date"],
                        "status": app["status"],
                    }
                )
    return rows


def activity_for(software_id: int) -> list[dict]:
    samples = {
        1: [
            {"when": "Today 08:42", "title": "Removed from PC-101", "meta": "Agent cleanup · Finance", "tone": "warning"},
            {"when": "Yesterday 16:10", "title": "Updated on PC-012", "meta": "135 → 139 · Corporate Services", "tone": ""},
            {"when": "Yesterday 09:05", "title": "Installed on PC-004", "meta": "Agent inventory sync", "tone": "success"},
            {"when": "2 days ago", "title": "Deployment #101 started", "meta": "Finance · 20 computers", "tone": ""},
        ],
        5: [
            {"when": "Today 07:18", "title": "Blacklist alert on PC-108", "meta": "Unauthorized detection", "tone": "danger"},
            {"when": "3 days ago", "title": "Quarantine policy applied", "meta": "Auto-remove enabled", "tone": "warning"},
        ],
    }
    return samples.get(
        software_id,
        [
            {"when": "Yesterday", "title": "Inventory reconciled", "meta": "Agent sync", "tone": ""},
            {"when": "Last week", "title": "Catalog entry updated", "meta": "IT Operations", "tone": ""},
        ],
    )


def versions_for(software_id: int) -> list[dict]:
    s = get_software(software_id)
    if not s:
        return []
    installs = installations_for(software_id)
    counts: dict[str, int] = {}
    for row in installs:
        counts[row["version"]] = counts.get(row["version"], 0) + 1
    if not counts:
        counts[s["version"]] = s["installed_count"]
    rows = []
    for ver, count in sorted(counts.items(), key=lambda x: x[0], reverse=True):
        rows.append(
            {
                "version": ver,
                "computers": count,
                "is_latest": ver == s["latest_version"] or ver.startswith(s["latest_version"][:6]),
                "status": "Current" if ver == s.get("latest_version") or ver == s["version"] else "Older",
            }
        )
    return rows


def security_for(software_id: int) -> dict:
    s = get_software(software_id) or {}
    cves = []
    if software_id == 4:
        cves = [
            {"id": "CVE-2025-54257", "severity": "High", "summary": "Arbitrary code via crafted PDF", "status": "Patched in catalog version"},
        ]
    elif software_id == 5:
        cves = [
            {"id": "CVE-2024-XXXX", "severity": "Critical", "summary": "Remote code execution in DHT module", "status": "Blacklisted — remove"},
        ]
    elif software_id == 7:
        cves = [
            {"id": "CVE-2025-XXXX", "severity": "Medium", "summary": "Privilege escalation in hypervisor bridge", "status": "Update available"},
        ]
    return {
        "score": s.get("security_score", 80),
        "risk": s.get("security_risk", "Low"),
        "cves": cves,
        "note": "CVE feed is a future integration — sample findings for UI review.",
    }


def get_software(software_id: int) -> dict | None:
    for s in catalog():
        if s["id"] == software_id:
            return s
    return None


def build_module_payload() -> dict:
    return {
        "kpis": kpis(),
        "catalog": catalog(),
        "computers": computers_with_software(),
        "deployments": deployments(),
        "updates": updates(),
        "requests": requests(),
        "blacklist": blacklist(),
        "licenses": license_rows(),
    }


def build_detail_payload(software_id: int) -> dict | None:
    s = get_software(software_id)
    if not s:
        return None
    return {
        "software": s,
        "installations": installations_for(software_id),
        "versions": versions_for(software_id),
        "deployments": [d for d in deployments() if d["software_id"] == software_id],
        "updates": [u for u in updates() if u["software_id"] == software_id],
        "security": security_for(software_id),
        "activity": activity_for(software_id),
        "license": s.get("license"),
    }
