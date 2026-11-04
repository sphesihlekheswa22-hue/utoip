"""Minimal SNMPv2c GET/SET client (no native deps)."""
from __future__ import annotations

import socket
from typing import Any


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _encode_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def _encode_integer(n: int) -> bytes:
    if n == 0:
        return _encode_tlv(0x02, b"\x00")
    length = (n.bit_length() + 8) // 8  # include sign bit
    raw = n.to_bytes(length, "big", signed=True)
    return _encode_tlv(0x02, raw)


def _encode_octet_string(s: str | bytes) -> bytes:
    raw = s.encode("utf-8") if isinstance(s, str) else s
    return _encode_tlv(0x04, raw)


def _encode_null() -> bytes:
    return b"\x05\x00"


def _encode_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.lstrip(".").split(".") if p != ""]
    if len(parts) < 2:
        raise ValueError(f"Invalid OID: {oid}")
    body = bytes([40 * parts[0] + parts[1]])
    for n in parts[2:]:
        if n < 0:
            raise ValueError(f"Invalid OID component: {n}")
        stack: list[int] = []
        stack.append(n & 0x7F)
        n >>= 7
        while n:
            stack.append(0x80 | (n & 0x7F))
            n >>= 7
        body += bytes(reversed(stack))
    return _encode_tlv(0x06, body)


def _encode_sequence(items: bytes) -> bytes:
    return _encode_tlv(0x30, items)


def _build_pdu(pdu_type: int, request_id: int, varbinds: list[tuple[str, bytes]]) -> bytes:
    vb_list = b"".join(_encode_sequence(_encode_oid(oid) + value) for oid, value in varbinds)
    pdu = (
        _encode_integer(request_id)
        + _encode_integer(0)  # error-status
        + _encode_integer(0)  # error-index
        + _encode_sequence(vb_list)
    )
    return _encode_tlv(pdu_type, pdu)


def _build_message(community: str, pdu: bytes) -> bytes:
    return _encode_sequence(
        _encode_integer(1)  # version SNMPv2c = 1
        + _encode_octet_string(community)
        + pdu
    )


def _decode_length(data: bytes, i: int) -> tuple[int, int]:
    first = data[i]
    i += 1
    if first < 0x80:
        return first, i
    n = first & 0x7F
    length = int.from_bytes(data[i : i + n], "big")
    return length, i + n


def _decode_tlv(data: bytes, i: int) -> tuple[int, bytes, int]:
    tag = data[i]
    length, i = _decode_length(data, i + 1)
    value = data[i : i + length]
    return tag, value, i + length


def _decode_integer(value: bytes) -> int:
    return int.from_bytes(value, "big", signed=True)


def _decode_oid(value: bytes) -> str:
    if not value:
        return ""
    first = value[0]
    parts = [first // 40, first % 40]
    n = 0
    for b in value[1:]:
        n = (n << 7) | (b & 0x7F)
        if not (b & 0x80):
            parts.append(n)
            n = 0
    return ".".join(str(p) for p in parts)


def _decode_varbinds(value: bytes) -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []
    i = 0
    while i < len(value):
        tag, seq, i = _decode_tlv(value, i)
        if tag != 0x30:
            break
        j = 0
        _, oid_raw, j = _decode_tlv(seq, j)
        oid = _decode_oid(oid_raw)
        vtag, vraw, _ = _decode_tlv(seq, j)
        if vtag == 0x02:
            decoded: Any = _decode_integer(vraw)
        elif vtag == 0x04:
            try:
                decoded = vraw.decode("utf-8")
            except UnicodeDecodeError:
                decoded = vraw.hex()
        elif vtag in (0x05, 0x80, 0x81, 0x82):  # NULL / noSuch*
            decoded = None
        elif vtag == 0x06:
            decoded = _decode_oid(vraw)
        elif vtag == 0x41:  # Counter32
            decoded = int.from_bytes(vraw, "big", signed=False)
        elif vtag == 0x42:  # Gauge32
            decoded = int.from_bytes(vraw, "big", signed=False)
        elif vtag == 0x43:  # TimeTicks
            decoded = int.from_bytes(vraw, "big", signed=False)
        elif vtag == 0x46:  # Counter64
            decoded = int.from_bytes(vraw, "big", signed=False)
        else:
            decoded = vraw.hex()
        results.append((oid, decoded))
    return results


def _parse_response(packet: bytes) -> list[tuple[str, Any]]:
    _, msg, _ = _decode_tlv(packet, 0)
    i = 0
    _, _, i = _decode_tlv(msg, i)  # version
    _, _, i = _decode_tlv(msg, i)  # community
    pdu_tag, pdu, _ = _decode_tlv(msg, i)
    if pdu_tag not in (0xA2, 0xA1):  # GetResponse / GetNextResponse
        # still try to parse
        pass
    j = 0
    _, _, j = _decode_tlv(pdu, j)  # request-id
    _, err_status, j = _decode_tlv(pdu, j)
    err = _decode_integer(err_status)
    _, _, j = _decode_tlv(pdu, j)  # error-index
    _, vb, _ = _decode_tlv(pdu, j)
    if err != 0:
        raise RuntimeError(f"SNMP error-status={err}")
    return _decode_varbinds(vb)


def snmp_get(
    host: str,
    community: str,
    oids: list[str],
    *,
    port: int = 161,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """SNMPv2c GET. Returns {oid: value}."""
    request_id = 1
    varbinds = [(oid, _encode_null()) for oid in oids]
    pdu = _build_pdu(0xA0, request_id, varbinds)  # GetRequest
    packet = _build_message(community, pdu)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(65535)
    finally:
        sock.close()
    decoded = _parse_response(data)
    # Map by requested OID string form (response may omit leading dots)
    out: dict[str, Any] = {}
    for oid, val in decoded:
        key = oid if oid.startswith(".") else f".{oid}"
        out[key] = val
        out[oid.lstrip(".")] = val
    return out


def snmp_get_next(
    host: str,
    community: str,
    oid: str,
    *,
    port: int = 161,
    timeout: float = 2.0,
) -> tuple[str, Any]:
    request_id = 2
    pdu = _build_pdu(0xA1, request_id, [(oid, _encode_null())])  # GetNext
    packet = _build_message(community, pdu)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(65535)
    finally:
        sock.close()
    decoded = _parse_response(data)
    if not decoded:
        raise RuntimeError("Empty SNMP GetNext response")
    next_oid, val = decoded[0]
    if not next_oid.startswith("."):
        next_oid = f".{next_oid}"
    return next_oid, val


def snmp_walk(
    host: str,
    community: str,
    root_oid: str,
    *,
    port: int = 161,
    timeout: float = 2.0,
    max_items: int = 64,
) -> list[tuple[str, Any]]:
    root = root_oid if root_oid.startswith(".") else f".{root_oid}"
    current = root
    items: list[tuple[str, Any]] = []
    for _ in range(max_items):
        next_oid, val = snmp_get_next(host, community, current, port=port, timeout=timeout)
        if not (next_oid == root or next_oid.startswith(root + ".")):
            break
        items.append((next_oid, val))
        current = next_oid
    return items


def snmp_set_integer(
    host: str,
    community: str,
    oid: str,
    value: int,
    *,
    port: int = 161,
    timeout: float = 2.0,
) -> None:
    """SNMPv2c SET of an INTEGER."""
    request_id = 3
    pdu = _build_pdu(0xA3, request_id, [(oid, _encode_integer(value))])  # SetRequest
    packet = _build_message(community, pdu)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(65535)
    finally:
        sock.close()
    _parse_response(data)
