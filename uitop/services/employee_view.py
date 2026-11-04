"""Employee self-service views — own devices, tickets, and personal dashboard."""
from __future__ import annotations

from flask import request, session

from uitop.extensions import db
from uitop.models.assets import Asset, AssetAssignment
from uitop.models.helpdesk import Ticket
from uitop.models.inventory import Computer
from uitop.models.user import User
from uitop.services import device_detection as detect
from uitop.services import helpdesk as hd_svc
from uitop.services.notifications import unread_count


def current_user_id() -> int | None:
    return session.get("user_id")


def load_user(user_id: int | None = None) -> User | None:
    uid = user_id or current_user_id()
    if not uid:
        return None
    return db.session.get(User, uid)


def _client_ip() -> str | None:
    try:
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        if forwarded:
            return forwarded
        return request.remote_addr
    except RuntimeError:
        return None


def list_my_devices(user_id: int | None = None) -> dict:
    """Real devices only: agent-detected PCs claimed for this user + nearby printers."""
    user = load_user(user_id)
    if user is None:
        return {
            "computers": [],
            "assets": [],
            "printers": [],
            "user": None,
            "detected": [],
            "needs_agent": True,
        }

    # Auto-detect & claim this workstation from agent / IP / local hostname
    claimed = detect.detect_and_claim_for_user(user, remote_addr=_client_ip())
    detection_by_id = {item["computer"].id: item["source"] for item in claimed}

    computers: list[dict] = []
    assets: list[dict] = []
    seen_pc: set[int] = set()
    seen_host: set[str] = set()
    seen_asset: set[int] = set()

    def resolve_computer(pc: Computer | None) -> Computer | None:
        if pc is None or not detect.is_real_agent_computer(pc):
            return None
        host = (pc.hostname or "").strip()
        if not host:
            return pc
        newest = (
            Computer.query.filter(Computer.hostname.ilike(host), Computer.agent_id.isnot(None))
            .order_by(Computer.last_seen_at.desc())
            .first()
        )
        if newest and detect.is_real_agent_computer(newest):
            return newest
        return pc

    def add_computer(pc: Computer, source: str | None = None):
        pc = resolve_computer(pc)
        if pc is None or pc.id in seen_pc:
            return
        host_key = (pc.hostname or "").strip().lower()
        if host_key and host_key in seen_host:
            return
        seen_pc.add(pc.id)
        if host_key:
            seen_host.add(host_key)
        computers.append(
            detect.serialize_detected_computer(
                pc, source=source or detection_by_id.get(pc.id)
            )
        )

    # From open assignments / custodianship (real agent PCs only)
    assignments = (
        AssetAssignment.query.filter_by(user_id=user.id, returned_at=None)
        .order_by(AssetAssignment.assigned_at.desc())
        .all()
    )
    for row in assignments:
        asset = row.asset
        if asset is None or asset.id in seen_asset:
            continue
        if asset.linked_type == "computer" and asset.linked_id:
            pc = db.session.get(Computer, asset.linked_id)
            if pc and detect.is_real_agent_computer(pc):
                seen_asset.add(asset.id)
                item = asset.to_dict()
                item["assigned_at"] = row.assigned_at.isoformat() if row.assigned_at else None
                item["detection_source"] = detection_by_id.get(pc.id) or "assigned"
                assets.append(item)
                add_computer(pc, detection_by_id.get(pc.id) or "assigned")

    for asset in Asset.query.filter_by(custodian_user_id=user.id).all():
        if asset.id in seen_asset:
            continue
        if asset.linked_type == "computer" and asset.linked_id:
            pc = db.session.get(Computer, asset.linked_id)
            if pc and detect.is_real_agent_computer(pc):
                seen_asset.add(asset.id)
                item = asset.to_dict()
                item["detection_source"] = detection_by_id.get(pc.id) or "custodian"
                assets.append(item)
                add_computer(pc, detection_by_id.get(pc.id) or "custodian")

    # Include freshly detected even if assignment lagged
    for item in claimed:
        add_computer(item["computer"], item["source"])

    pc_models = [db.session.get(Computer, c["id"]) for c in computers]
    pc_models = [c for c in pc_models if c]
    printers = detect.real_office_printers(user, pc_models)

    return {
        "user": user,
        "computers": computers,
        "assets": assets,
        "printers": printers,
        "detected": [
            {"hostname": i["computer"].hostname, "source": i["source"]} for i in claimed
        ],
        "needs_agent": len(computers) == 0,
    }


def list_my_tickets(user_id: int | None = None, *, status: str | None = None) -> list[dict]:
    uid = user_id or current_user_id()
    if not uid:
        return []
    return hd_svc.list_tickets(requester_user_id=uid, status=status)


def build_employee_home(user_id: int | None = None) -> dict:
    user = load_user(user_id)
    uid = user.id if user else None
    devices = list_my_devices(uid)
    tickets = list_my_tickets(uid)
    open_tickets = [t for t in tickets if t.get("status") not in ("resolved", "closed")]
    return {
        "user": user,
        "devices": devices,
        "tickets_open": open_tickets[:8],
        "tickets_open_count": len(open_tickets),
        "tickets_total": len(tickets),
        "device_count": len(devices["computers"]),
        "printer_count": len(devices["printers"]),
        "unread_notifications": unread_count(uid) if uid else 0,
        "needs_agent": devices.get("needs_agent"),
        "announcements": [
            {
                "title": "Need IT help?",
                "body": "Ask IT Copilot for password, printer, or Wi-Fi tips — or open a Help Desk ticket.",
            },
            {
                "title": "Your devices",
                "body": "UITOP shows PCs that have the UITOP Agent installed and reporting — not demo inventory.",
            },
        ],
    }


def user_owns_ticket(ticket_id: int, user_id: int | None = None) -> bool:
    uid = user_id or current_user_id()
    if not uid:
        return False
    ticket = db.session.get(Ticket, ticket_id)
    return bool(ticket and ticket.requester_user_id == uid)
