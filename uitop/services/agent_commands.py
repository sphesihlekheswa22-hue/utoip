"""Remote agent command queue — restart, lock, sync, diagnostics, etc."""
from __future__ import annotations

import socket
from datetime import datetime, timezone

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.agent_telemetry import AgentCommand
from uitop.models.inventory import Computer
from uitop.services.audit import log_audit

ALLOWED_COMMANDS = frozenset(
    {
        "restart",
        "shutdown",
        "lock",
        "logoff",
        "sync_inventory",
        "collect_diagnostics",
        "wake_on_lan",
    }
)

COMMAND_LABELS = {
    "restart": "Restart Computer",
    "shutdown": "Shutdown",
    "lock": "Lock workstation",
    "logoff": "Log off",
    "sync_inventory": "Sync inventory",
    "collect_diagnostics": "Collect diagnostics",
    "wake_on_lan": "Wake on LAN",
}


def utcnow():
    return datetime.now(timezone.utc)


def queue_command(
    *,
    computer_id: int,
    command: str,
    created_by_id: int | None = None,
    params: dict | None = None,
) -> AgentCommand:
    cmd = (command or "").strip().lower()
    if cmd not in ALLOWED_COMMANDS:
        raise ValidationError(f"Unsupported command: {command}")

    computer = Computer.query.get(computer_id)
    if computer is None:
        raise NotFoundError("Computer not found")

    # Wake-on-LAN is executed on the server immediately (no agent needed)
    if cmd == "wake_on_lan":
        mac = (computer.mac_address or "").strip()
        if not mac:
            raise ValidationError("This computer has no MAC address — cannot send Wake-on-LAN")
        try:
            _send_wol(mac)
            result_msg = f"Magic packet sent to {mac}"
            status = "completed"
        except OSError as exc:
            result_msg = f"WoL failed: {exc}"
            status = "failed"
        row = AgentCommand(
            agent_id=computer.agent_id or "server",
            computer_id=computer.id,
            command=cmd,
            status=status,
            params=params or {},
            result=result_msg,
            created_by_id=created_by_id,
            sent_at=utcnow(),
            completed_at=utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        log_audit(
            "agents.command",
            actor_user_id=created_by_id,
            resource_type="computer",
            resource_id=computer.id,
            meta={"command": cmd, "status": status},
        )
        return row

    if not computer.agent_id:
        raise ValidationError("No UITOP agent enrolled on this computer — install the agent first")

    row = AgentCommand(
        agent_id=computer.agent_id,
        computer_id=computer.id,
        command=cmd,
        status="pending",
        params=params or {},
        created_by_id=created_by_id,
    )
    db.session.add(row)
    db.session.commit()
    log_audit(
        "agents.command",
        actor_user_id=created_by_id,
        resource_type="computer",
        resource_id=computer.id,
        meta={"command": cmd, "command_id": row.id},
    )
    return row


def list_commands_for_computer(computer_id: int, *, limit: int = 20) -> list[AgentCommand]:
    return (
        AgentCommand.query.filter_by(computer_id=computer_id)
        .order_by(AgentCommand.created_at.desc())
        .limit(limit)
        .all()
    )


def claim_pending_commands(agent_id: str, *, limit: int = 10) -> list[AgentCommand]:
    """Mark pending commands as sent and return them for the agent to run."""
    rows = (
        AgentCommand.query.filter_by(agent_id=agent_id, status="pending")
        .order_by(AgentCommand.created_at.asc())
        .limit(limit)
        .all()
    )
    now = utcnow()
    for row in rows:
        row.status = "sent"
        row.sent_at = now
    if rows:
        db.session.commit()
    return rows


def complete_command(
    command_id: int,
    *,
    agent_id: str,
    status: str,
    result: str | None = None,
) -> AgentCommand:
    row = AgentCommand.query.get(command_id)
    if row is None or row.agent_id != agent_id:
        raise NotFoundError("Command not found")
    st = (status or "").strip().lower()
    if st not in {"completed", "failed"}:
        raise ValidationError("status must be completed or failed")
    row.status = st
    row.result = (result or "")[:4000]
    row.completed_at = utcnow()
    db.session.commit()
    return row


def _send_wol(mac: str) -> None:
    cleaned = mac.replace("-", "").replace(":", "").replace(".", "").upper()
    if len(cleaned) != 12:
        raise ValidationError(f"Invalid MAC address: {mac}")
    mac_bytes = bytes.fromhex(cleaned)
    packet = b"\xff" * 6 + mac_bytes * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, ("255.255.255.255", 9))
    finally:
        sock.close()
