"""Execute allowed remote commands on the local Windows host."""
from __future__ import annotations

import platform
import socket
import subprocess
from datetime import datetime, timezone


def execute_command(command: str, params: dict | None = None) -> str:
    cmd = (command or "").strip().lower()
    params = params or {}
    if cmd == "restart":
        delay = int(params.get("delay_seconds") or 30)
        _run(["shutdown", "/r", "/t", str(delay), "/c", "UITOP remote restart"])
        return f"Restart scheduled in {delay}s"
    if cmd == "shutdown":
        delay = int(params.get("delay_seconds") or 30)
        _run(["shutdown", "/s", "/t", str(delay), "/c", "UITOP remote shutdown"])
        return f"Shutdown scheduled in {delay}s"
    if cmd == "lock":
        _run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Workstation lock requested"
    if cmd == "logoff":
        _run(["shutdown", "/l"])
        return "Logoff requested"
    if cmd == "sync_inventory":
        return "SYNC_INVENTORY"  # caller should run inventory report
    if cmd == "collect_diagnostics":
        return _collect_diagnostics()
    raise RuntimeError(f"Unsupported command: {command}")


def _run(argv: list[str]) -> None:
    creationflags = 0
    if platform.system() == "Windows":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        creationflags=creationflags,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        # shutdown /l returns non-zero in some sessions — still often works
        if "logoff" not in " ".join(argv).lower():
            raise RuntimeError(err)


def _collect_diagnostics() -> str:
    import psutil

    uname = platform.uname()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
    lines = [
        f"collected_at={datetime.now(timezone.utc).isoformat()}",
        f"hostname={socket.gethostname()}",
        f"os={uname.system} {uname.release} {uname.version}",
        f"cpu_percent={psutil.cpu_percent(interval=0.5)}",
        f"memory_percent={mem.percent}",
        f"memory_used_gb={round(mem.used / (1024**3), 2)}",
        f"disk_percent={disk.percent}",
        f"boot_time={datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat()}",
        f"process_count={len(psutil.pids())}",
    ]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lines.append(f"ip={s.getsockname()[0]}")
        s.close()
    except OSError:
        pass
    return "\n".join(lines)
