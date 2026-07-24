"""Licenses — enterprise seat/compliance mock data (system of record for Software)."""
from __future__ import annotations

from datetime import date, timedelta


def _status(expiry: str, available: int, purchased: int, assigned: int) -> str:
    if assigned > purchased:
        return "Overused"
    exp = date.fromisoformat(expiry)
    today = date(2026, 7, 23)
    if exp < today:
        return "Expired"
    if exp <= today + timedelta(days=90):
        return "Warning"
    if available == 0:
        return "Fully assigned"
    return "Active"


def licenses() -> list[dict]:
    rows = [
        {
            "id": 1,
            "product": "Microsoft 365 Apps",
            "vendor": "Microsoft",
            "type": "Subscription",
            "sku": "O365-E3-UMZ",
            "purchased": 250,
            "assigned": 231,
            "cost_annual": 187500,
            "currency": "ZAR",
            "expiry": "2027-05-10",
            "start": "2024-05-11",
            "po_number": "PO-2024-0881",
            "contract": "Microsoft Enterprise Agreement",
            "software_id": 2,
            "owner": "IT Operations",
            "notes": "Municipal EA — includes Teams and SharePoint Online.",
        },
        {
            "id": 2,
            "product": "Adobe Acrobat Pro",
            "vendor": "Adobe",
            "type": "Subscription",
            "sku": "ACR-PRO-50",
            "purchased": 50,
            "assigned": 67,
            "cost_annual": 89500,
            "currency": "ZAR",
            "expiry": "2026-11-01",
            "start": "2025-11-01",
            "po_number": "PO-2025-1204",
            "contract": "Adobe VIP",
            "software_id": 4,
            "owner": "Corporate Services",
            "notes": "Over-assigned vs seats — reclaim or buy 20 more.",
        },
        {
            "id": 3,
            "product": "AutoCAD 2025",
            "vendor": "Autodesk",
            "type": "Subscription",
            "sku": "ACAD-2025-30",
            "purchased": 30,
            "assigned": 22,
            "cost_annual": 312000,
            "currency": "ZAR",
            "expiry": "2026-12-31",
            "start": "2026-01-01",
            "po_number": "PO-2025-1440",
            "contract": "Autodesk AEC Collection",
            "software_id": 9,
            "owner": "Technical Services",
            "notes": "Named-user licenses for Engineering draughting.",
        },
        {
            "id": 4,
            "product": "Docker Desktop Business",
            "vendor": "Docker Inc.",
            "type": "Subscription",
            "sku": "DOCKER-BIZ-25",
            "purchased": 25,
            "assigned": 18,
            "cost_annual": 67500,
            "currency": "ZAR",
            "expiry": "2026-09-01",
            "start": "2025-09-01",
            "po_number": "PO-2025-0912",
            "contract": None,
            "software_id": 7,
            "owner": "IT Operations",
            "notes": "Developer workstations only.",
        },
        {
            "id": 5,
            "product": "Windows Server 2022 Datacenter",
            "vendor": "Microsoft",
            "type": "Perpetual",
            "sku": "WS2022-DC-16C",
            "purchased": 4,
            "assigned": 4,
            "cost_annual": 0,
            "currency": "ZAR",
            "expiry": "2029-06-30",
            "start": "2023-06-30",
            "po_number": "PO-2023-0550",
            "contract": "Microsoft Enterprise Agreement",
            "software_id": None,
            "owner": "IT Operations",
            "notes": "Core licenses for virtualization hosts — SA active until 2029.",
        },
        {
            "id": 6,
            "product": "Kaspersky Endpoint Security",
            "vendor": "Kaspersky",
            "type": "Subscription",
            "sku": "KES-500",
            "purchased": 500,
            "assigned": 468,
            "cost_annual": 142000,
            "currency": "ZAR",
            "expiry": "2026-08-15",
            "start": "2025-08-15",
            "po_number": "PO-2025-0777",
            "contract": "Kaspersky Municipal Bundle",
            "software_id": None,
            "owner": "IT Security",
            "notes": "Endpoint AV across all enrolled PCs.",
        },
        {
            "id": 7,
            "product": "Zoom Workplace Pro",
            "vendor": "Zoom",
            "type": "Subscription",
            "sku": "ZOOM-PRO-200",
            "purchased": 200,
            "assigned": 198,
            "cost_annual": 96000,
            "currency": "ZAR",
            "expiry": "2027-01-20",
            "start": "2026-01-20",
            "po_number": "PO-2026-0018",
            "contract": None,
            "software_id": 8,
            "owner": "Corporate Services",
            "notes": "Nearly fully assigned.",
        },
        {
            "id": 8,
            "product": "SQL Server 2019 Standard",
            "vendor": "Microsoft",
            "type": "Perpetual",
            "sku": "SQL2019-STD-2",
            "purchased": 2,
            "assigned": 2,
            "cost_annual": 0,
            "currency": "ZAR",
            "expiry": "2025-12-01",
            "start": "2020-12-01",
            "po_number": "PO-2020-0331",
            "contract": "Microsoft Enterprise Agreement",
            "software_id": None,
            "owner": "IT Operations",
            "notes": "Software Assurance lapsed — renew or migrate.",
        },
    ]
    for r in rows:
        r["available"] = r["purchased"] - r["assigned"]
        r["status"] = _status(r["expiry"], r["available"], r["purchased"], r["assigned"])
        r["utilization"] = round((r["assigned"] / r["purchased"]) * 100) if r["purchased"] else 0
    return rows


def kpis() -> dict:
    rows = licenses()
    today = date(2026, 7, 23)
    soon = today + timedelta(days=90)
    total = len(rows)
    active = sum(1 for r in rows if r["status"] in ("Active", "Fully assigned", "Warning"))
    expiring = sum(1 for r in rows if r["status"] == "Warning")
    expired = sum(1 for r in rows if r["status"] == "Expired")
    available = sum(max(0, r["available"]) for r in rows)
    overused = sum(1 for r in rows if r["status"] == "Overused")
    # Compliance: penalize overuse and expired
    score = 100 - overused * 12 - expired * 10 - expiring * 3
    score = max(55, min(100, score))
    return {
        "total": total,
        "active": active,
        "expiring": expiring,
        "expired": expired,
        "available_seats": available,
        "compliance_score": score,
        "overused": overused,
    }


def assigned_users(license_id: int) -> list[dict]:
    samples = {
        1: [
            {"name": "K. Zulu", "email": "kzulu@umzinyathi.gov.za", "department": "Finance", "assigned": "2025-08-14", "seat": "User"},
            {"name": "L. Mokoena", "email": "lmokoena@umzinyathi.gov.za", "department": "Corporate Services", "assigned": "2025-08-14", "seat": "User"},
            {"name": "S. Dlamini", "email": "sdlamini@umzinyathi.gov.za", "department": "IT Operations", "assigned": "2025-09-01", "seat": "User"},
            {"name": "J. Botha", "email": "jbotha@umzinyathi.gov.za", "department": "Technical Services", "assigned": "2025-10-02", "seat": "User"},
            {"name": "N. Naidoo", "email": "nnaidoo@umzinyathi.gov.za", "department": "Engineering", "assigned": "2026-01-12", "seat": "User"},
        ],
        2: [
            {"name": "Finance Desk", "email": "finance@umzinyathi.gov.za", "department": "Finance", "assigned": "2025-11-05", "seat": "Shared"},
            {"name": "SCM Office", "email": "scm@umzinyathi.gov.za", "department": "Finance", "assigned": "2025-11-05", "seat": "Shared"},
            {"name": "K. Zulu", "email": "kzulu@umzinyathi.gov.za", "department": "Finance", "assigned": "2026-02-01", "seat": "User"},
        ],
        3: [
            {"name": "N. Naidoo", "email": "nnaidoo@umzinyathi.gov.za", "department": "Engineering", "assigned": "2026-01-05", "seat": "Named"},
            {"name": "T. Mthembu", "email": "tmthembu@umzinyathi.gov.za", "department": "Engineering", "assigned": "2026-01-05", "seat": "Named"},
        ],
    }
    return samples.get(
        license_id,
        [
            {"name": "IT Operations pool", "email": "itops@umzinyathi.gov.za", "department": "IT Operations", "assigned": "2025-01-01", "seat": "Pool"},
        ],
    )


def assigned_devices(license_id: int) -> list[dict]:
    samples = {
        1: [
            {"hostname": "PC-001", "user": "K. Zulu", "department": "Finance", "assigned": "2025-08-14"},
            {"hostname": "PC-014", "user": "L. Mokoena", "department": "Corporate Services", "assigned": "2025-08-14"},
            {"hostname": "PC-020", "user": "S. Dlamini", "department": "IT Operations", "assigned": "2025-09-01"},
            {"hostname": "PC-108", "user": "J. Botha", "department": "Technical Services", "assigned": "2025-10-02"},
            {"hostname": "Sphesihle", "user": "IT Admin", "department": "IT Operations", "assigned": "2026-07-15"},
        ],
        2: [
            {"hostname": "PC-001", "user": "K. Zulu", "department": "Finance", "assigned": "2025-09-01"},
            {"hostname": "FIN-SCAN-02", "user": "Finance Desk", "department": "Finance", "assigned": "2025-11-05"},
        ],
        4: [
            {"hostname": "PC-020", "user": "S. Dlamini", "department": "IT Operations", "assigned": "2026-04-12"},
            {"hostname": "Sphesihle", "user": "IT Admin", "department": "IT Operations", "assigned": "2026-03-01"},
        ],
        3: [
            {"hostname": "PC-108", "user": "J. Botha", "department": "Technical Services", "assigned": "2025-12-05"},
            {"hostname": "ENG-WS-04", "user": "N. Naidoo", "department": "Engineering", "assigned": "2026-01-05"},
        ],
    }
    return samples.get(license_id, [])


def purchase_info(license_id: int) -> dict:
    lic = get_license(license_id) or {}
    return {
        "po_number": lic.get("po_number"),
        "vendor": lic.get("vendor"),
        "order_date": lic.get("start"),
        "cost_annual": lic.get("cost_annual"),
        "currency": lic.get("currency", "ZAR"),
        "contract": lic.get("contract"),
        "sku": lic.get("sku"),
        "reseller": "DFA / Microsoft CSP" if lic.get("vendor") == "Microsoft" else "Regional VAR",
        "payment_terms": "Net 30",
        "cost_centre": "ICT Operations",
    }


def renewals(license_id: int) -> list[dict]:
    samples = {
        1: [
            {"date": "2024-05-11", "action": "Initial EA enrolment", "seats": 200, "term": "3 years", "cost": 150000},
            {"date": "2025-05-11", "action": "Seat uplift +50", "seats": 250, "term": "Remaining EA", "cost": 37500},
            {"date": "2027-05-10", "action": "Scheduled renewal", "seats": 250, "term": "3 years", "cost": 195000},
        ],
        2: [
            {"date": "2024-11-01", "action": "VIP start · 40 seats", "seats": 40, "term": "1 year", "cost": 72000},
            {"date": "2025-11-01", "action": "Renewed · +10 seats", "seats": 50, "term": "1 year", "cost": 89500},
        ],
        8: [
            {"date": "2020-12-01", "action": "Perpetual purchase + SA", "seats": 2, "term": "SA 3yr", "cost": 180000},
            {"date": "2023-12-01", "action": "SA renewed", "seats": 2, "term": "2 years", "cost": 42000},
            {"date": "2025-12-01", "action": "SA expired — not renewed", "seats": 2, "term": "—", "cost": 0},
        ],
    }
    return samples.get(
        license_id,
        [
            {"date": "—", "action": "No renewal history in demo set", "seats": 0, "term": "—", "cost": 0},
        ],
    )


def activity(license_id: int) -> list[dict]:
    samples = {
        1: [
            {"when": "Today 10:12", "title": "Seat assigned to N. Naidoo", "meta": "Engineering · User seat", "tone": "success"},
            {"when": "Yesterday", "title": "Compliance check passed", "meta": "231 / 250 utilized", "tone": ""},
            {"when": "3 days ago", "title": "PO-2024-0881 linked", "meta": "Purchase record", "tone": ""},
        ],
        2: [
            {"when": "Today 07:40", "title": "Overuse alert raised", "meta": "67 assigned / 50 purchased", "tone": "danger"},
            {"when": "Yesterday", "title": "Reclaim candidate list generated", "meta": "12 idle 90+ days", "tone": "warning"},
            {"when": "Last week", "title": "Renewal reminder (90 days)", "meta": "Expires 2026-11-01", "tone": "warning"},
        ],
        8: [
            {"when": "2025-12-01", "title": "License marked Expired", "meta": "Software Assurance lapsed", "tone": "danger"},
            {"when": "2025-11-01", "title": "Renewal notice ignored", "meta": "Budget hold", "tone": "warning"},
        ],
    }
    return samples.get(
        license_id,
        [
            {"when": "Last week", "title": "Catalog reconciled", "meta": "IT Operations", "tone": ""},
            {"when": "Last month", "title": "Seat count verified", "meta": "Audit sample", "tone": ""},
        ],
    )


def get_license(license_id: int) -> dict | None:
    for row in licenses():
        if row["id"] == license_id:
            return row
    return None


def build_module_payload() -> dict:
    return {"kpis": kpis(), "licenses": licenses()}


def build_detail_payload(license_id: int) -> dict | None:
    lic = get_license(license_id)
    if not lic:
        return None
    return {
        "license": lic,
        "users": assigned_users(license_id),
        "devices": assigned_devices(license_id),
        "purchase": purchase_info(license_id),
        "renewals": renewals(license_id),
        "activity": activity(license_id),
    }
