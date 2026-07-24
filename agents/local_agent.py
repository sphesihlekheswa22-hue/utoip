"""
UITOP Local Agent — reports THIS Windows PC to the UITOP backend.

Usage (from project root, with Flask running on port 5500):

  python agents/local_agent.py
  python agents/local_agent.py --once
  python agents/local_agent.py --server http://127.0.0.1:5500

First run creates an enrollment token via the API admin login, registers
this machine, and saves credentials to agents/agent_credentials.json.
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import time
import uuid
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Install psutil first:  pip install psutil")
    sys.exit(1)

try:
    import urllib.error
    import urllib.request
except ImportError:
    raise

ROOT = Path(__file__).resolve().parent
CREDS_FILE = ROOT / "agent_credentials.json"
DEFAULT_SERVER = "http://127.0.0.1:5500"
ADMIN_EMAIL = "admin@umzinyathi.gov.za"
ADMIN_PASSWORD = "Admin@UITOP2026"


def http_json(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach UITOP at {url}. Is the server running? ({exc.reason})"
        ) from exc


def get_mac() -> str:
    node = uuid.getnode()
    return ":".join(f"{(node >> ele) & 0xFF:02X}" for ele in range(40, -1, -8))


def primary_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def collect_inventory() -> dict:
    uname = platform.uname()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
    return {
        "hostname": socket.gethostname(),
        "os_name": f"{uname.system} {uname.release}",
        "os_version": uname.version,
        "manufacturer": platform.machine(),
        "model": platform.processor() or uname.machine,
        "serial_number": str(uuid.getnode()),
        "ip_address": primary_ip(),
        "mac_address": get_mac(),
        "cpu_model": platform.processor() or uname.processor,
        "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count(),
        "ram_gb": round(mem.total / (1024**3), 1),
        "disk_gb": round(disk.total / (1024**3), 1),
        "domain": socket.getfqdn(),
        "agent_version": "local-1.0.0",
    }


def collect_performance() -> dict:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
    net = psutil.net_io_counters()
    # Short sample for CPU
    cpu = psutil.cpu_percent(interval=0.8)
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_used_mb": round(mem.used / (1024**2), 1),
        "memory_total_mb": round(mem.total / (1024**2), 1),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "network_bytes_sent": net.bytes_sent,
        "network_bytes_recv": net.bytes_recv,
        "process_count": len(psutil.pids()),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


def load_creds() -> dict | None:
    if not CREDS_FILE.exists():
        return None
    return json.loads(CREDS_FILE.read_text(encoding="utf-8"))


def save_creds(data: dict) -> None:
    CREDS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved credentials -> {CREDS_FILE}")


def enroll(server: str) -> dict:
    print("Logging in as admin to create enrollment token…")
    login = http_json(
        "POST",
        f"{server}/api/v1/auth/login",
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    admin_token = login["data"]["tokens"]["access_token"]

    print("Creating enrollment token…")
    created = http_json(
        "POST",
        f"{server}/api/v1/agents/enrollment-tokens",
        {"label": f"Local agent {socket.gethostname()}", "expires_hours": 168, "max_uses": 5},
        token=admin_token,
    )
    enroll_token = created["data"]["token"]

    hostname = socket.gethostname()
    print(f"Registering this PC as {hostname}…")
    reg = http_json(
        "POST",
        f"{server}/api/v1/agents/register",
        {"enrollment_token": enroll_token, "hostname": hostname, "agent_version": "local-1.0.0"},
    )["data"]

    creds = {
        "server": server,
        "client_id": reg["client_id"],
        "client_secret": reg["client_secret"],
        "agent_id": reg["agent_id"],
        "computer_id": reg.get("computer_id"),
        "hostname": hostname,
    }
    save_creds(creds)
    return creds


def agent_access_token(server: str, creds: dict) -> str:
    result = http_json(
        "POST",
        f"{server}/api/v1/agents/token",
        {"client_id": creds["client_id"], "client_secret": creds["client_secret"]},
    )
    return result["data"]["access_token"]


def report_once(server: str, access: str) -> None:
    inv = collect_inventory()
    perf = collect_performance()
    print(f"Reporting {inv['hostname']} ({inv['ip_address']})…")

    hb = http_json(
        "POST",
        f"{server}/api/v1/agents/heartbeat",
        {
            "status": "online",
            "agent_version": "local-1.0.0",
            "hostname": inv["hostname"],
            "ip_address": inv["ip_address"],
        },
        token=access,
    )["data"]
    print(f"  heartbeat OK · status={hb.get('status')} · last_seen={hb.get('last_seen_at')}")

    http_json("POST", f"{server}/api/v1/agents/inventory", inv, token=access)
    print(f"  inventory OK · {inv['os_name']} · RAM {inv['ram_gb']} GB · Disk {inv['disk_gb']} GB")

    http_json(
        "POST",
        f"{server}/api/v1/agents/performance",
        {"samples": [perf]},
        token=access,
    )
    print(
        f"  performance OK · CPU {perf['cpu_percent']}% · "
        f"Mem {perf['memory_percent']}% · Disk {perf['disk_percent']}%"
    )

    http_json(
        "POST",
        f"{server}/api/v1/agents/events",
        {
            "events": [
                {
                    "event_type": "agent.report",
                    "message": f"Live report from {inv['hostname']}",
                    "severity": "info",
                    "source": "local_agent",
                }
            ]
        },
        token=access,
    )
    print("  event OK")


def main() -> int:
    parser = argparse.ArgumentParser(description="UITOP local PC agent")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UITOP base URL")
    parser.add_argument("--once", action="store_true", help="Send one report and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between reports")
    parser.add_argument("--reset", action="store_true", help="Delete saved credentials and re-enroll")
    args = parser.parse_args()

    server = args.server.rstrip("/")

    if args.reset and CREDS_FILE.exists():
        CREDS_FILE.unlink()
        print("Cleared saved credentials.")

    creds = load_creds()
    if creds is None:
        try:
            creds = enroll(server)
        except RuntimeError as exc:
            print(f"Enrollment failed: {exc}")
            return 1
    else:
        server = creds.get("server", server)
        print(f"Using saved agent {creds.get('agent_id')} for {creds.get('hostname')}")

    try:
        access = agent_access_token(server, creds)
    except RuntimeError as exc:
        print(f"Token exchange failed: {exc}")
        return 1

    if args.once:
        try:
            report_once(server, access)
        except RuntimeError as exc:
            print(f"Report failed: {exc}")
            return 1
        print(f"\nOpen Computers: {server}/computers/")
        return 0

    print(f"Live mode — reporting every {args.interval}s. Press Ctrl+C to stop.")
    print(f"Open Computers: {server}/computers/\n")
    while True:
        try:
            access = agent_access_token(server, creds)
            report_once(server, access)
            print("")
            time.sleep(max(5, args.interval))
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except RuntimeError as exc:
            print(f"Report failed: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
