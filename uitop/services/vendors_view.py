"""Vendors — enterprise supplier hub mock data (links ready for assets/software/POs)."""
from __future__ import annotations


CATEGORIES = [
    "Hardware",
    "Software",
    "Networking",
    "Printers",
    "Cloud Services",
    "Security",
    "Telecommunications",
    "Maintenance",
]


def vendors() -> list[dict]:
    return [
        {
            "id": 1,
            "name": "Dell Technologies",
            "category": "Hardware",
            "status": "Active",
            "preferred": True,
            "website": "https://www.dell.com",
            "rating": 4.6,
            "description": "Primary OEM for desktops, laptops, and servers across Umzinyathi IT.",
            "contact_name": "John Smith",
            "email": "john.smith@dell.com",
            "phone": "+27 11 555 0101",
            "mobile": "+27 82 555 0101",
            "support_email": "support.za@dell.com",
            "support_phone": "+27 861 335 563",
            "sla": "Next Business Day",
            "address": "Woodmead North Office Park, Johannesburg",
            "city": "Johannesburg",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "2191",
            "tax_number": "4XXXXXXXX",
            "registration": "1999/XXXXXX/07",
            "account_number": "UMZ-DELL-2044",
            "payment_terms": "Net 30",
            "notes": "Preferred hardware vendor. Use Dell ProSupport for critical servers.",
            "assets_count": 245,
            "contracts_count": 3,
            "open_pos": 2,
            "software_count": 0,
        },
        {
            "id": 2,
            "name": "Microsoft",
            "category": "Software",
            "status": "Active",
            "preferred": True,
            "website": "https://www.microsoft.com",
            "rating": 4.8,
            "description": "Enterprise Agreement partner for M365, Windows, and SQL Server.",
            "contact_name": "Jane Doe",
            "email": "jane.doe@microsoft.com",
            "phone": "+27 11 555 0202",
            "mobile": "+27 83 555 0202",
            "support_email": "csspza@microsoft.com",
            "support_phone": "+27 11 269 5500",
            "sla": "Premier Support",
            "address": "Microsoft Campus, Johannesburg",
            "city": "Johannesburg",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "2196",
            "tax_number": "4YYYYYYYY",
            "registration": "N/A",
            "account_number": "UMZ-MSFT-EA",
            "payment_terms": "Net 45",
            "notes": "EA renews May 2027. CSP for overflow seats.",
            "assets_count": 12,
            "contracts_count": 2,
            "open_pos": 1,
            "software_count": 6,
        },
        {
            "id": 3,
            "name": "Cisco Systems",
            "category": "Networking",
            "status": "Active",
            "preferred": True,
            "website": "https://www.cisco.com",
            "rating": 4.5,
            "description": "Core switching, wireless, and firewall estate.",
            "contact_name": "Thabo Molefe",
            "email": "tmolefe@cisco.com",
            "phone": "+27 11 555 0303",
            "mobile": "+27 84 555 0303",
            "support_email": "tac@cisco.com",
            "support_phone": "+27 11 555 0399",
            "sla": "24x7 Critical",
            "address": "Sandton City Office Tower",
            "city": "Sandton",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "2196",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-CISCO-11",
            "payment_terms": "Net 30",
            "notes": "SmartNet contracts on core switches.",
            "assets_count": 64,
            "contracts_count": 1,
            "open_pos": 0,
            "software_count": 1,
        },
        {
            "id": 4,
            "name": "Adobe",
            "category": "Software",
            "status": "Active",
            "preferred": False,
            "website": "https://www.adobe.com",
            "rating": 3.9,
            "description": "Acrobat VIP and creative cloud seats for selected departments.",
            "contact_name": "Priya Naidoo",
            "email": "pnaidoo@adobe.com",
            "phone": "+27 21 555 0404",
            "mobile": None,
            "support_email": "enterprise@adobe.com",
            "support_phone": "+27 21 555 0499",
            "sla": "Business hours",
            "address": "Cape Town CBD",
            "city": "Cape Town",
            "province": "Western Cape",
            "country": "South Africa",
            "postal_code": "8001",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-ADOBE-VIP",
            "payment_terms": "Net 30",
            "notes": "Over-licensed Acrobat — reclaim before renew.",
            "assets_count": 0,
            "contracts_count": 1,
            "open_pos": 0,
            "software_count": 2,
        },
        {
            "id": 5,
            "name": "HP Inc.",
            "category": "Printers",
            "status": "Active",
            "preferred": False,
            "website": "https://www.hp.com",
            "rating": 4.1,
            "description": "Fleet printers and managed print supplies.",
            "contact_name": "Sipho Dlamini",
            "email": "sdlamini@hp.com",
            "phone": "+27 31 555 0505",
            "mobile": "+27 71 555 0505",
            "support_email": "printcare.za@hp.com",
            "support_phone": "+27 861 103 103",
            "sla": "Next Business Day",
            "address": "Umhlanga Ridge",
            "city": "Durban",
            "province": "KwaZulu-Natal",
            "country": "South Africa",
            "postal_code": "4319",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-HP-PRINT",
            "payment_terms": "Net 30",
            "notes": "Toner under MPS contract.",
            "assets_count": 38,
            "contracts_count": 1,
            "open_pos": 1,
            "software_count": 0,
        },
        {
            "id": 6,
            "name": "Kaspersky Lab",
            "category": "Security",
            "status": "Active",
            "preferred": True,
            "website": "https://www.kaspersky.co.za",
            "rating": 4.3,
            "description": "Endpoint security across enrolled PCs.",
            "contact_name": "Lebo Khumalo",
            "email": "lkhumalo@kaspersky.com",
            "phone": "+27 11 555 0606",
            "mobile": None,
            "support_email": "support@kaspersky.com",
            "support_phone": "+27 11 555 0699",
            "sla": "24x7 Endpoint",
            "address": "Bryanston",
            "city": "Johannesburg",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "2191",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-KAS-500",
            "payment_terms": "Net 30",
            "notes": "500-seat municipal bundle expires Aug 2026.",
            "assets_count": 0,
            "contracts_count": 1,
            "open_pos": 0,
            "software_count": 1,
        },
        {
            "id": 7,
            "name": "Vodacom Business",
            "category": "Telecommunications",
            "status": "Active",
            "preferred": False,
            "website": "https://www.vodacom.co.za",
            "rating": 3.7,
            "description": "APN, MPLS, and mobile data for field staff.",
            "contact_name": "Account Manager · Municipal",
            "email": "municipal@vodacom.co.za",
            "phone": "+27 82 123 4567",
            "mobile": "+27 82 123 4567",
            "support_email": "enterprise.support@vodacom.co.za",
            "support_phone": "082 123 4567",
            "sla": "Business hours",
            "address": "Vodacom World, Midrand",
            "city": "Midrand",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "1685",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-VODA-APN",
            "payment_terms": "Net 30",
            "notes": "ISP contract renews annually.",
            "assets_count": 0,
            "contracts_count": 1,
            "open_pos": 0,
            "software_count": 0,
        },
        {
            "id": 8,
            "name": "Datacentrix",
            "category": "Maintenance",
            "status": "Active",
            "preferred": False,
            "website": "https://www.datacentrix.co.za",
            "rating": 4.0,
            "description": "On-site break/fix and hardware maintenance partner.",
            "contact_name": "Field Ops Desk",
            "email": "field@datacentrix.co.za",
            "phone": "+27 12 555 0808",
            "mobile": None,
            "support_email": "noc@datacentrix.co.za",
            "support_phone": "+27 12 555 0899",
            "sla": "4-hour critical",
            "address": "Centurion Gate",
            "city": "Centurion",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "0157",
            "tax_number": None,
            "registration": None,
            "account_number": "UMZ-DCX-MNT",
            "payment_terms": "Net 30",
            "notes": "Used for motherboard / power supply swaps.",
            "assets_count": 0,
            "contracts_count": 1,
            "open_pos": 0,
            "software_count": 0,
        },
        {
            "id": 9,
            "name": "Legacy SoftSupply",
            "category": "Software",
            "status": "Archived",
            "preferred": False,
            "website": None,
            "rating": 2.5,
            "description": "Former reseller — archived after EA moved to Microsoft direct.",
            "contact_name": "—",
            "email": "accounts@softsupply.example",
            "phone": "+27 11 000 0000",
            "mobile": None,
            "support_email": None,
            "support_phone": None,
            "sla": None,
            "address": "—",
            "city": "Pretoria",
            "province": "Gauteng",
            "country": "South Africa",
            "postal_code": "0001",
            "tax_number": None,
            "registration": None,
            "account_number": "ARCHIVED",
            "payment_terms": "—",
            "notes": "Do not place new orders.",
            "assets_count": 0,
            "contracts_count": 0,
            "open_pos": 0,
            "software_count": 0,
        },
    ]


def kpis() -> dict:
    rows = vendors()
    active = [v for v in rows if v["status"] == "Active"]
    return {
        "total": len(rows),
        "active": len(active),
        "preferred": sum(1 for v in rows if v.get("preferred") and v["status"] == "Active"),
        "contracts_expiring": 4,
        "assets_supplied": sum(v["assets_count"] for v in active),
        "open_pos": sum(v["open_pos"] for v in active),
    }


def get_vendor(vendor_id: int) -> dict | None:
    for v in vendors():
        if v["id"] == vendor_id:
            return v
    return None


def assets_for(vendor_id: int) -> list[dict]:
    samples = {
        1: [
            {"tag": "UMZ-AST-10001", "name": "Dell OptiPlex 7010", "type": "Computer", "assignee": "K. Zulu", "status": "In use"},
            {"tag": "UMZ-AST-10014", "name": "Dell Latitude 5540", "type": "Laptop", "assignee": "L. Mokoena", "status": "In use"},
            {"tag": "UMZ-AST-10020", "name": "PowerEdge R650", "type": "Server", "assignee": "IT Operations", "status": "In use"},
            {"tag": "UMZ-AST-10088", "name": "Dell Monitor P2422H", "type": "Peripheral", "assignee": "Finance Desk", "status": "In store"},
        ],
        3: [
            {"tag": "UMZ-AST-20001", "name": "Catalyst 9300", "type": "Network", "assignee": "Core LAN", "status": "In use"},
            {"tag": "UMZ-AST-20012", "name": "Meraki MR46", "type": "Network", "assignee": "HQ Wi‑Fi", "status": "In use"},
        ],
        5: [
            {"tag": "UMZ-AST-30002", "name": "HP LaserJet MFP", "type": "Printer", "assignee": "Finance floor", "status": "In use"},
            {"tag": "UMZ-AST-30008", "name": "HP DesignJet", "type": "Printer", "assignee": "Engineering", "status": "In use"},
        ],
        2: [
            {"tag": "UMZ-AST-40001", "name": "Surface Hub (shared)", "type": "Peripheral", "assignee": "Boardroom A", "status": "In use"},
        ],
    }
    return samples.get(vendor_id, [])


def software_for(vendor_id: int) -> list[dict]:
    samples = {
        2: [
            {"name": "Microsoft 365 Apps", "category": "Productivity", "license_id": 1, "software_id": 2},
            {"name": "Windows 11 Enterprise", "category": "OS", "license_id": None, "software_id": None},
            {"name": "SQL Server 2019", "category": "Database", "license_id": 8, "software_id": None},
            {"name": "Windows Server 2022", "category": "Server OS", "license_id": 5, "software_id": None},
        ],
        4: [
            {"name": "Adobe Acrobat Pro", "category": "Productivity", "license_id": 2, "software_id": 4},
            {"name": "Adobe Photoshop", "category": "Creative", "license_id": None, "software_id": None},
        ],
        6: [
            {"name": "Kaspersky Endpoint Security", "category": "Security", "license_id": 6, "software_id": None},
        ],
        3: [
            {"name": "Cisco DNA Center", "category": "Network mgmt", "license_id": None, "software_id": None},
        ],
    }
    return samples.get(vendor_id, [])


def contracts_for(vendor_id: int) -> list[dict]:
    samples = {
        1: [
            {"name": "Dell ProSupport Plus", "start": "2024-01-01", "end": "2027-01-01", "renewal": "2026-10-01", "status": "Active"},
            {"name": "Dell Warranty — OptiPlex fleet", "start": "2025-03-01", "end": "2028-03-01", "renewal": "2027-12-01", "status": "Active"},
            {"name": "Dell EMC storage care", "start": "2023-06-01", "end": "2026-06-01", "renewal": "2026-03-01", "status": "Expiring"},
        ],
        2: [
            {"name": "Microsoft Enterprise Agreement", "start": "2024-05-11", "end": "2027-05-10", "renewal": "2027-02-10", "status": "Active"},
            {"name": "Premier Support", "start": "2025-05-11", "end": "2026-05-10", "renewal": "2026-02-10", "status": "Expiring"},
        ],
        3: [
            {"name": "Cisco SmartNet — Core", "start": "2025-01-01", "end": "2026-12-31", "renewal": "2026-10-01", "status": "Active"},
        ],
        4: [
            {"name": "Adobe VIP", "start": "2025-11-01", "end": "2026-11-01", "renewal": "2026-08-01", "status": "Expiring"},
        ],
        5: [
            {"name": "HP Managed Print Services", "start": "2025-02-01", "end": "2028-02-01", "renewal": "2027-11-01", "status": "Active"},
        ],
        6: [
            {"name": "Kaspersky Municipal Bundle", "start": "2025-08-15", "end": "2026-08-15", "renewal": "2026-05-15", "status": "Expiring"},
        ],
        7: [
            {"name": "Vodacom Business APN", "start": "2025-07-01", "end": "2026-06-30", "renewal": "2026-04-01", "status": "Active"},
        ],
        8: [
            {"name": "Datacentrix Break/Fix", "start": "2025-01-01", "end": "2025-12-31", "renewal": "2025-10-01", "status": "Expired"},
        ],
    }
    return samples.get(vendor_id, [])


def purchase_orders_for(vendor_id: int) -> list[dict]:
    samples = {
        1: [
            {"number": "PO-2026-0142", "date": "2026-07-02", "amount": 485000, "status": "Open", "items": "20× Latitude 5540"},
            {"number": "PO-2026-0091", "date": "2026-05-18", "amount": 128000, "status": "Open", "items": "Monitors + docks"},
            {"number": "PO-2025-1440", "date": "2025-11-20", "amount": 920000, "status": "Received", "items": "PowerEdge R650"},
        ],
        2: [
            {"number": "PO-2026-0018", "date": "2026-01-15", "amount": 37500, "status": "Received", "items": "M365 seat uplift"},
        ],
        5: [
            {"number": "PO-2026-0110", "date": "2026-06-01", "amount": 24000, "status": "Open", "items": "Toner pack Q3"},
        ],
    }
    return samples.get(vendor_id, [])


def warranties_for(vendor_id: int) -> list[dict]:
    samples = {
        1: [
            {"asset": "Dell OptiPlex 7010", "tag": "UMZ-AST-10001", "term": "3 Years", "expires": "2028-01-12", "status": "Active"},
            {"asset": "PowerEdge R650", "tag": "UMZ-AST-10020", "term": "5 Years ProSupport", "expires": "2028-11-20", "status": "Active"},
            {"asset": "Latitude 5540", "tag": "UMZ-AST-10014", "term": "3 Years", "expires": "2026-08-14", "status": "Expiring"},
        ],
        3: [
            {"asset": "Catalyst 9300", "tag": "UMZ-AST-20001", "term": "SmartNet 24x7", "expires": "2026-12-31", "status": "Active"},
        ],
        5: [
            {"asset": "HP LaserJet MFP", "tag": "UMZ-AST-30002", "term": "1 Year + MPS", "expires": "2026-09-01", "status": "Expiring"},
        ],
    }
    return samples.get(vendor_id, [])


def contacts_for(vendor_id: int) -> list[dict]:
    v = get_vendor(vendor_id)
    if not v:
        return []
    rows = [
        {
            "name": v["contact_name"],
            "role": "Primary account",
            "email": v["email"],
            "phone": v["phone"],
            "primary": True,
        }
    ]
    if v.get("support_email"):
        rows.append(
            {
                "name": "Support desk",
                "role": "Technical support",
                "email": v["support_email"],
                "phone": v.get("support_phone") or "—",
                "primary": False,
            }
        )
    extras = {
        1: [{"name": "Orders desk", "role": "Order management", "email": "orders.za@dell.com", "phone": "+27 11 555 0199", "primary": False}],
        2: [{"name": "Licensing specialist", "role": "EA / CSP", "email": "licensing@microsoft.com", "phone": "+27 11 269 5511", "primary": False}],
    }
    rows.extend(extras.get(vendor_id, []))
    return rows


def activity_for(vendor_id: int) -> list[dict]:
    samples = {
        1: [
            {"when": "Today", "title": "Open PO-2026-0142 acknowledged", "meta": "20× Latitude · ETA 14 days", "tone": ""},
            {"when": "Yesterday", "title": "Updated primary contact", "meta": "John Smith mobile verified", "tone": ""},
            {"when": "3 days ago", "title": "Warranty sync — OptiPlex fleet", "meta": "2 assets expiring < 60 days", "tone": "warning"},
            {"when": "Last week", "title": "Received PO-2025-1440", "meta": "PowerEdge R650 → asset created", "tone": "success"},
        ],
        2: [
            {"when": "Today", "title": "EA compliance check", "meta": "231 / 250 M365 seats", "tone": ""},
            {"when": "Yesterday", "title": "Premier Support ticket opened", "meta": "SQL failover advisory", "tone": ""},
            {"when": "Last month", "title": "Seat uplift purchased", "meta": "PO-2026-0018", "tone": "success"},
        ],
        9: [
            {"when": "2025-03-01", "title": "Vendor archived", "meta": "Moved to Microsoft direct", "tone": "warning"},
            {"when": "2024-11-12", "title": "Final invoice closed", "meta": "Account UMZ-SOFT-OLD", "tone": ""},
        ],
    }
    return samples.get(
        vendor_id,
        [
            {"when": "Last week", "title": "Vendor profile reviewed", "meta": "IT Operations", "tone": ""},
            {"when": "Last month", "title": "Contact verified", "meta": "Quarterly supplier check", "tone": ""},
        ],
    )


def build_module_payload() -> dict:
    return {"kpis": kpis(), "vendors": vendors(), "categories": CATEGORIES}


def build_detail_payload(vendor_id: int) -> dict | None:
    v = get_vendor(vendor_id)
    if not v:
        return None
    return {
        "vendor": v,
        "assets": assets_for(vendor_id),
        "software": software_for(vendor_id),
        "contracts": contracts_for(vendor_id),
        "purchase_orders": purchase_orders_for(vendor_id),
        "warranties": warranties_for(vendor_id),
        "contacts": contacts_for(vendor_id),
        "activity": activity_for(vendor_id),
    }
