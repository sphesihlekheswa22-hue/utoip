"""
UITOP Local Agent — reports THIS Windows PC to the UITOP backend.

Usage:

  # Preferred: enroll with a token from Computers → Install Agent
  python local_agent.py --server http://10.0.0.7:5500 --token YOUR_TOKEN

  # One-shot report then exit
  python local_agent.py --server http://10.0.0.7:5500 --token YOUR_TOKEN --once

  # Dev only (this PC): auto-create a token via admin login
  python local_agent.py --server http://127.0.0.1:5500

Credentials are saved next to this script (or under %%LOCALAPPDATA%%\\UITOP\\agent).
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
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

AGENT_VERSION = "1.1.0"
DEFAULT_SERVER = "http://127.0.0.1:5500"


def _creds_path() -> Path:
    env = os.getenv("UITOP_AGENT_HOME")
    if env:
        base = Path(env)
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UITOP" / "agent"
    else:
        base = Path.home() / ".uitop" / "agent"
    base.mkdir(parents=True, exist_ok=True)
    return base / "agent_credentials.json"


CREDS_FILE = _creds_path()


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
            f"Cannot reach UITOP at {url}. Is the server running and reachable on the LAN? ({exc.reason})"
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
    try:
        logged_in = getpass.getuser()
    except Exception:
        logged_in = ""
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
        "agent_version": AGENT_VERSION,
        "logged_in_user": logged_in,
        "windows_user": logged_in,
    }


def collect_performance() -> dict:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
    net = psutil.net_io_counters()
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


def enroll_with_pairing_code(server: str, code: str) -> dict:
    hostname = socket.gethostname()
    print(f"Pairing this PC as {hostname}…")
    reg = http_json(
        "POST",
        f"{server}/api/v1/agents/pair",
        {
            "code": code.strip(),
            "hostname": hostname,
            "agent_version": AGENT_VERSION,
        },
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


def enroll_with_token(server: str, enroll_token: str) -> dict:
    hostname = socket.gethostname()
    print(f"Registering this PC as {hostname}…")
    reg = http_json(
        "POST",
        f"{server}/api/v1/agents/register",
        {
            "enrollment_token": enroll_token,
            "hostname": hostname,
            "agent_version": AGENT_VERSION,
        },
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


def enroll_via_admin(server: str) -> dict:
    """Dev helper — creates a short-lived enrollment token using admin login."""
    email = os.getenv("UITOP_ADMIN_EMAIL", "admin@umzinyathi.gov.za")
    password = os.getenv("UITOP_ADMIN_PASSWORD", "Admin@UITOP2026")
    print("No --token provided; creating enrollment token via admin login (dev only)…")
    login = http_json(
        "POST",
        f"{server}/api/v1/auth/login",
        {"email": email, "password": password},
    )
    admin_token = login["data"]["tokens"]["access_token"]
    created = http_json(
        "POST",
        f"{server}/api/v1/agents/enrollment-tokens",
        {"label": f"Local agent {socket.gethostname()}", "expires_hours": 168, "max_uses": 5},
        token=admin_token,
    )
    return enroll_with_token(server, created["data"]["token"])


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
            "agent_version": AGENT_VERSION,
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


def poll_and_run_commands(server: str, access: str) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from command_exec import execute_command
    except ImportError:
        return
    try:
        payload = http_json("GET", f"{server}/api/v1/agents/commands", token=access)
    except RuntimeError:
        return
    commands = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(commands, list) or not commands:
        return
    for item in commands:
        if not isinstance(item, dict):
            continue
        cmd_id = item.get("id")
        command = item.get("command") or ""
        try:
            result = execute_command(command, item.get("params") or {})
            if result == "SYNC_INVENTORY":
                report_once(server, access)
                result = "Inventory sync completed"
            http_json(
                "POST",
                f"{server}/api/v1/agents/commands/{cmd_id}/result",
                {"status": "completed", "result": result},
                token=access,
            )
            print(f"  command {command} OK · {result}")
        except Exception as exc:  # noqa: BLE001
            try:
                http_json(
                    "POST",
                    f"{server}/api/v1/agents/commands/{cmd_id}/result",
                    {"status": "failed", "result": str(exc)},
                    token=access,
                )
            except RuntimeError:
                pass
            print(f"  command {command} FAILED · {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="UITOP local PC agent")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UITOP base URL (use LAN IP for other PCs)")
    parser.add_argument("--token", default="", help="Enrollment token (advanced)")
    parser.add_argument("--code", default="", help="6-digit pairing code (simple install)")
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
            if args.code:
                creds = enroll_with_pairing_code(server, args.code)
            elif args.token:
                creds = enroll_with_token(server, args.token.strip())
            else:
                creds = enroll_via_admin(server)
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

    print(f"Live mode — reporting every {args.interval}s · polling commands every 5s. Press Ctrl+C to stop.")
    print(f"Open Computers: {server}/computers/\n")
    last_report = 0.0
    while True:
        try:
            access = agent_access_token(server, creds)
            now = time.time()
            if now - last_report >= max(5, args.interval):
                report_once(server, access)
                last_report = now
                print("")
            poll_and_run_commands(server, access)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except RuntimeError as exc:
            print(f"Report failed: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
