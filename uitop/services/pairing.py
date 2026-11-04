"""Short pairing codes for simple agent enrollment (no long tokens)."""
from __future__ import annotations

import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from uitop.core.errors import UnauthorizedError, ValidationError
from uitop.services import agents as agents_service

_PAIR_TTL_MINUTES = 15
_codes: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _purge_expired() -> None:
    now = _utcnow()
    expired = [c for c, row in _codes.items() if row["expires_at"] <= now]
    for c in expired:
        _codes.pop(c, None)


def create_pairing_code(*, created_by_id: int | None, label: str = "Pair device") -> dict[str, Any]:
    """Create a 6-digit code linked to a single-use enrollment token."""
    _purge_expired()
    token, raw = agents_service.create_enrollment_token(
        label=label,
        created_by_id=created_by_id,
        expires_hours=1,  # underlying token backup expiry
        max_uses=1,
    )
    expires_at = _utcnow() + timedelta(minutes=_PAIR_TTL_MINUTES)

    with _lock:
        for _ in range(20):
            code = f"{random.randint(0, 999999):06d}"
            if code not in _codes:
                break
        else:
            raise ValidationError("Could not allocate pairing code — try again")

        _codes[code] = {
            "code": code,
            "enrollment_token": raw,
            "token_id": token.id,
            "expires_at": expires_at,
            "created_by_id": created_by_id,
            "used": False,
        }

    return {
        "code": code,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": int(_PAIR_TTL_MINUTES * 60),
        "token_id": token.id,
    }


def get_active_pairing_code() -> dict[str, Any] | None:
    """Return the newest non-expired unused code, if any."""
    _purge_expired()
    with _lock:
        active = [r for r in _codes.values() if not r["used"]]
    if not active:
        return None
    row = max(active, key=lambda r: r["expires_at"])
    return {
        "code": row["code"],
        "expires_at": row["expires_at"].isoformat(),
        "expires_in_seconds": max(0, int((row["expires_at"] - _utcnow()).total_seconds())),
    }


def pair_with_code(
    code: str,
    *,
    hostname: str | None = None,
    agent_version: str | None = None,
) -> dict[str, Any]:
    """Exchange a pairing code for agent credentials (public enrollment)."""
    raw = (code or "").strip()
    if not raw or not raw.isdigit() or len(raw) != 6:
        raise ValidationError("Enter the 6-digit pairing code from UITOP")

    _purge_expired()
    with _lock:
        row = _codes.get(raw)
        if row is None:
            raise UnauthorizedError("Invalid or expired pairing code")
        if row["used"]:
            raise UnauthorizedError("This pairing code was already used")
        if row["expires_at"] <= _utcnow():
            _codes.pop(raw, None)
            raise UnauthorizedError("Pairing code expired — generate a new one on UITOP")
        row["used"] = True
        enroll_token = row["enrollment_token"]

    result = agents_service.register_agent(
        enrollment_token=enroll_token,
        hostname=hostname,
        agent_version=agent_version,
    )
    result["paired"] = True
    return result
