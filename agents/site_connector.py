#!/usr/bin/env python3
"""UITOP Site Connector — scans the local LAN and pushes results to cloud UITOP.

Run on one always-on PC inside the organization network (not on Render).

First-time enroll:
  python site_connector.py --server https://your-app.onrender.com --token enroll_xxx --site "HQ"

After enroll (credentials saved under %%LOCALAPPDATA%%\\UITOP\\site-connector\\):
  python site_connector.py --once
  python site_connector.py --interval 3600

Env:
  UITOP_SERVER, UITOP_ENROLL_TOKEN, UITOP_SITE_NAME
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
DEFAULT_SERVER = "http://127.0.0.1:5500"

_PROBE_PORTS = (22, 80, 139, 443, 445, 515, 631, 3389, 5985, 9100)
_TCP_TIMEOUT = 0.35
_PING_TIMEOUT_MS = 400
_WORKERS = 48


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def home_dir() -> Path:
    env = os.getenv("UITOP_CONNECTOR_HOME")
    if env:
        return Path(env)
    if platform.system().lower() == "windows":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        return base / "UITOP" / "site-connector"
    return Path.home() / ".uitop" / "site-connector"


def creds_path() -> Path:
    return home_dir() / "credentials.json"


def load_creds() -> dict[str, Any] | None:
    path = creds_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_creds(data: dict[str, Any]) -> None:
    d = home_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = creds_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def http_json(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json", "User-Agent": f"UITOP-SiteConnector/{VERSION}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail[:500]}") from exc


def api_data(resp: dict) -> dict:
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"] or {}
    return resp


def detect_local_cidrs() -> list[str]:
    found: set[str] = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            if net.is_private:
                found.add(str(net))
    except OSError:
        pass
    # Also try UDP trick for primary outbound interface
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            if net.is_private:
                found.add(str(net))
    except OSError:
        pass
    return sorted(found) or ["192.168.1.0/24"]


def local_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def _ping(ip: str) -> bool:
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(_PING_TIMEOUT_MS), ip]
    else:
        timeout_s = max(1, int(_PING_TIMEOUT_MS / 1000) or 1)
        cmd = ["ping", "-c", "1", "-W", str(timeout_s), ip]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _scan_ports(ip: str) -> list[int]:
    open_ports: list[int] = []
    for port in _PROBE_PORTS:
        try:
            with socket.create_connection((ip, port), timeout=_TCP_TIMEOUT):
                open_ports.append(port)
        except OSError:
            continue
    return open_ports


def _classify(ports: list[int]) -> str:
    ps = set(ports)
    if ps & {9100, 515, 631}:
        return "Printer"
    windows = bool(ps & {445, 139, 3389, 5985})
    if windows:
        if 22 in ps and 445 not in ps:
            return "Server"
        return "Computer"
    if 22 in ps:
        return "Server"
    if ps & {80, 443}:
        return "Network"
    if ports:
        return "Unknown"
    return "Unknown"


def _guess_os(ports: list[int], dtype: str) -> str:
    ps = set(ports)
    if dtype == "Printer":
        return "Printer firmware"
    if 445 in ps or 139 in ps or 3389 in ps or 5985 in ps:
        return "Windows"
    if 22 in ps:
        return "Linux / Unix"
    if dtype == "Network":
        return "Network OS"
    return "Unknown"


def probe_host(ip: str) -> dict[str, Any] | None:
    ping_ok = _ping(ip)
    open_ports = _scan_ports(ip)
    if not ping_ok and not open_ports:
        return None
    dtype = _classify(open_ports)
    return {
        "ip": ip,
        "hostname": ip,
        "name": ip,
        "type": dtype,
        "os": _guess_os(open_ports, dtype),
        "vendor": "—",
        "ports": open_ports,
        "status": "Online",
        "model": "Unknown",
    }


def scan_cidr(cidr: str) -> list[dict[str, Any]]:
    net = ipaddress.ip_network(cidr, strict=False)
    if not net.is_private:
        raise ValueError(f"Only private RFC1918 networks allowed: {cidr}")
    hosts = [str(h) for h in net.hosts()]
    if len(hosts) > 256:
        raise ValueError("CIDR wider than /24 is not allowed")
    results: list[dict[str, Any]] = []
    print(f"  Scanning {cidr} ({len(hosts)} hosts)…")
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(probe_host, ip): ip for ip in hosts}
        done = 0
        for fut in as_completed(futures):
            done += 1
            if done % 32 == 0 or done == len(hosts):
                print(f"    … {done}/{len(hosts)}")
            host = fut.result()
            if host:
                results.append(host)
    print(f"  Found {len(results)} live host(s)")
    return results


def maybe_snmp_snapshot(host: dict[str, Any], community: str = "public") -> dict[str, Any] | None:
    """Best-effort printer payload. Optional SNMP if uitop package is present on this host."""
    if host.get("type") != "Printer":
        return None
    ip = host["ip"]
    base = {
        "ip": ip,
        "name": host.get("hostname") or ip,
        "hostname": host.get("hostname") or ip,
        "model": host.get("model") or "Unknown",
        "ports": host.get("ports") or [],
        "status": "online",
        "snmp_ok": False,
    }
    try:
        from uitop.services.snmp_client import snmp_get  # type: ignore

        data = snmp_get(
            ip,
            community,
            [".1.3.6.1.2.1.1.1.0", ".1.3.6.1.2.1.1.5.0"],
            timeout=1.0,
        )
        descr = data.get(".1.3.6.1.2.1.1.1.0") or data.get("1.3.6.1.2.1.1.1.0")
        name = data.get(".1.3.6.1.2.1.1.5.0") or data.get("1.3.6.1.2.1.1.5.0")
        if descr or name:
            base["snmp_ok"] = True
            if name:
                base["name"] = str(name)
                base["hostname"] = str(name)
            if descr:
                base["snmp_sys_descr"] = str(descr)[:512]
                base["model"] = str(descr)[:120]
    except Exception:
        pass
    return base


def enroll(server: str, token: str, site_name: str, cidrs: list[str]) -> dict:
    host = socket.gethostname()
    print(f"Enrolling site connector as {site_name!r} → {server}")
    resp = http_json(
        "POST",
        f"{server}/api/v1/connectors/register",
        {
            "enrollment_token": token,
            "site_name": site_name,
            "hostname": host,
            "connector_version": VERSION,
            "cidrs": cidrs,
        },
    )
    data = api_data(resp)
    save_creds(
        {
            "server": server.rstrip("/"),
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "connector_id": data["connector_id"],
            "site_id": data["site_id"],
            "site_name": data.get("site_name") or site_name,
            "cidrs": cidrs,
        }
    )
    print(f"  Enrolled · connector_id={data['connector_id']} · site_id={data['site_id']}")
    print(f"  Credentials saved to {creds_path()}")
    return data


def get_access_token(creds: dict) -> str:
    resp = http_json(
        "POST",
        f"{creds['server']}/api/v1/connectors/token",
        {"client_id": creds["client_id"], "client_secret": creds["client_secret"]},
    )
    data = api_data(resp)
    return data["access_token"]


def run_cycle(creds: dict, cidrs: list[str], community: str = "public") -> None:
    token = get_access_token(creds)
    server = creds["server"]

    http_json(
        "POST",
        f"{server}/api/v1/connectors/heartbeat",
        {
            "status": "online",
            "connector_version": VERSION,
            "hostname": socket.gethostname(),
            "ip_address": local_ip(),
            "cidrs": cidrs,
        },
        token=token,
    )
    print("Heartbeat OK")

    all_hosts: list[dict[str, Any]] = []
    for cidr in cidrs:
        hosts = scan_cidr(cidr)
        all_hosts.extend(hosts)
        result = api_data(
            http_json(
                "POST",
                f"{server}/api/v1/connectors/network-scan",
                {"cidr": cidr, "scanned_at": utcnow_iso(), "hosts": hosts, "upsert": True},
                token=token,
            )
        )
        print(
            f"  Ingest {cidr}: created={result.get('created_count')} "
            f"updated={result.get('updated_count')}"
        )

    printers = []
    for h in all_hosts:
        snap = maybe_snmp_snapshot(h, community=community)
        if snap:
            printers.append(snap)
    if printers:
        result = api_data(
            http_json(
                "POST",
                f"{server}/api/v1/connectors/printers",
                {"scanned_at": utcnow_iso(), "printers": printers},
                token=token,
            )
        )
        print(f"  Printers: created={result.get('created_count')} updated={result.get('updated_count')}")

    http_json(
        "POST",
        f"{server}/api/v1/connectors/heartbeat",
        {
            "status": "online",
            "last_scan_at": utcnow_iso(),
            "stats": {"hosts_last_scan": len(all_hosts), "printers": len(printers)},
        },
        token=token,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="UITOP Site Connector")
    p.add_argument("--server", default=os.getenv("UITOP_SERVER", DEFAULT_SERVER))
    p.add_argument("--token", default=os.getenv("UITOP_ENROLL_TOKEN", ""))
    p.add_argument("--site", default=os.getenv("UITOP_SITE_NAME", ""), help="Site display name")
    p.add_argument("--cidr", action="append", dest="cidrs", help="CIDR to scan (repeatable)")
    p.add_argument("--community", default="public", help="SNMP community for printers")
    p.add_argument("--once", action="store_true", help="Scan once and exit")
    p.add_argument("--interval", type=int, default=3600, help="Seconds between scans (default 3600)")
    args = p.parse_args(argv)

    server = args.server.rstrip("/")
    creds = load_creds()

    cidrs = args.cidrs or (creds or {}).get("cidrs") or detect_local_cidrs()
    if isinstance(cidrs, str):
        cidrs = [cidrs]

    if args.token:
        site = args.site or socket.gethostname()
        enroll(server, args.token, site, cidrs)
        creds = load_creds()
    elif not creds:
        print("No credentials. Enroll with --token enroll_… --site \"HQ\"", file=sys.stderr)
        return 2

    assert creds is not None
    if args.cidrs:
        creds["cidrs"] = cidrs
        save_creds(creds)

    if args.once:
        run_cycle(creds, cidrs, community=args.community)
        return 0

    print(f"Site connector looping every {args.interval}s · server={creds['server']}")
    while True:
        try:
            run_cycle(creds, cidrs, community=args.community)
        except Exception as exc:  # noqa: BLE001
            print(f"Cycle error: {exc}", file=sys.stderr)
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
