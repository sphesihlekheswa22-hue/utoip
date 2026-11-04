"""
UITOP Agent — simple GUI for non-technical users.
Double-click to run. Enter UITOP address + 6-digit code.
No Python required when built as UITOP-Agent.exe.

Build:  powershell -File tools/build_agent.ps1
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

AGENT_VERSION = "2.2.0"
DEFAULT_SERVER = "http://127.0.0.1:5500"
REPORT_INTERVAL = 30
COMMAND_POLL_SECONDS = 5
RUN_VALUE_NAME = "UITOPAgent"


def _agent_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


sys.path.insert(0, str(_agent_dir()))
try:
    from command_exec import execute_command
except ImportError:
    from agents.command_exec import execute_command  # type: ignore


def _data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UITOP" / "agent"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _creds_path() -> Path:
    return _data_dir() / "agent_credentials.json"


def _config_path() -> Path:
    return _data_dir() / "agent_config.json"


def _installed_exe_path() -> Path:
    return _data_dir() / "UITOP-Agent.exe"


def http_json(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict:
    import urllib.error
    import urllib.request

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
            payload = json.loads(raw) if raw else {}
            if "data" in payload:
                return payload["data"]
            return payload
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(detail)
            msg = err.get("error", {}).get("message") or detail
        except json.JSONDecodeError:
            msg = detail
        raise RuntimeError(msg or f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach UITOP ({exc.reason}). Check the address and that UITOP is running.") from exc


def load_creds() -> dict | None:
    p = _creds_path()
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_creds(data: dict) -> None:
    _creds_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_config(server: str, *, autostart: bool | None = None) -> None:
    cfg = load_config()
    cfg["server"] = server
    if autostart is not None:
        cfg["autostart"] = bool(autostart)
    _config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def load_config() -> dict:
    p = _config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def install_local_copy() -> Path | None:
    """Copy running frozen exe into LOCALAPPDATA so Startup always finds it."""
    if not getattr(sys, "frozen", False):
        return Path(sys.argv[0]).resolve()
    src = Path(sys.executable).resolve()
    dest = _installed_exe_path()
    try:
        if src != dest:
            shutil.copy2(src, dest)
        return dest
    except OSError:
        return src


def enable_windows_autostart(exe_path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        # Start minimized so employees don't see a window every login
        cmd = f'"{exe_path}" --minimized'
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def disable_windows_autostart() -> None:
    if os.name != "nt":
        return
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except OSError:
        pass


def is_windows_autostart_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def collect_inventory() -> dict:
    import platform
    import uuid

    import psutil

    uname = platform.uname()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = socket.gethostbyname(socket.gethostname())
    node = uuid.getnode()
    mac = ":".join(f"{(node >> ele) & 0xFF:02X}" for ele in range(40, -1, -8))
    return {
        "hostname": socket.gethostname(),
        "os_name": f"{uname.system} {uname.release}",
        "os_version": uname.version,
        "manufacturer": platform.machine(),
        "model": platform.processor() or uname.machine,
        "serial_number": str(node),
        "ip_address": ip,
        "mac_address": mac,
        "cpu_model": platform.processor() or uname.processor,
        "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count(),
        "ram_gb": round(mem.total / (1024**3), 1),
        "disk_gb": round(disk.total / (1024**3), 1),
        "domain": socket.getfqdn(),
        "agent_version": AGENT_VERSION,
        "logged_in_user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "windows_user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
    }


def collect_performance() -> dict:
    import psutil

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
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


def pair_agent(server: str, code: str) -> dict:
    server = server.rstrip("/")
    reg = http_json(
        "POST",
        f"{server}/api/v1/agents/pair",
        {
            "code": code.strip(),
            "hostname": socket.gethostname(),
            "agent_version": AGENT_VERSION,
        },
    )
    creds = {
        "server": server,
        "client_id": reg["client_id"],
        "client_secret": reg["client_secret"],
        "agent_id": reg["agent_id"],
        "computer_id": reg.get("computer_id"),
        "hostname": socket.gethostname(),
    }
    save_creds(creds)
    save_config(server)
    return creds


def agent_access_token(server: str, creds: dict) -> str:
    result = http_json(
        "POST",
        f"{server}/api/v1/agents/token",
        {"client_id": creds["client_id"], "client_secret": creds["client_secret"]},
    )
    return result["access_token"]


def report_once(server: str, access: str) -> None:
    inv = collect_inventory()
    perf = collect_performance()
    http_json(
        "POST",
        f"{server}/api/v1/agents/heartbeat",
        {
            "status": "online",
            "agent_version": AGENT_VERSION,
            "hostname": inv["hostname"],
            "ip_address": inv["ip_address"],
        },
        token=access,
    )
    http_json("POST", f"{server}/api/v1/agents/inventory", inv, token=access)
    http_json("POST", f"{server}/api/v1/agents/performance", {"samples": [perf]}, token=access)


class AgentApp:
    def __init__(self, *, start_minimized: bool = False) -> None:
        self.root = tk.Tk()
        self.root.title("UITOP Agent")
        self.root.geometry("460x420")
        self.root.resizable(False, False)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_minimized = start_minimized
        self._status = tk.StringVar(value="Ask UITOP for a code (Connect my PC), then connect here.")
        self._build_ui()
        self._check_existing()
        if start_minimized and load_creds():
            self.root.after(200, self.root.iconify)

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 6}
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Connect this PC", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="No Python needed. Enter the address and code from UITOP.",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="UITOP address (from the website)").pack(anchor="w")
        self.server_var = tk.StringVar(value=load_config().get("server") or DEFAULT_SERVER)
        ttk.Entry(frame, textvariable=self.server_var, width=48).pack(fill=tk.X, **pad)

        ttk.Label(frame, text="6-digit code").pack(anchor="w")
        self.code_var = tk.StringVar()
        code_entry = ttk.Entry(frame, textvariable=self.code_var, width=14, font=("Segoe UI", 16))
        code_entry.pack(anchor="w", **pad)
        code_entry.bind("<KeyRelease>", self._format_code)

        self.autostart_var = tk.BooleanVar(value=load_config().get("autostart", True) or is_windows_autostart_enabled())
        ttk.Checkbutton(
            frame,
            text="Start automatically when I sign in to Windows",
            variable=self.autostart_var,
        ).pack(anchor="w", pady=(4, 8))

        self.connect_btn = ttk.Button(frame, text="Connect", command=self._on_connect)
        self.connect_btn.pack(anchor="w", pady=8)

        ttk.Label(frame, textvariable=self._status, wraplength=400, font=("Segoe UI", 9)).pack(
            anchor="w", pady=(8, 0)
        )

        ttk.Label(
            frame,
            text="Tip: In UITOP open Connect my PC → Get my code → copy the address.",
            font=("Segoe UI", 8),
            foreground="#666",
        ).pack(anchor="w", pady=(14, 0))

    def _format_code(self, _event=None) -> None:
        raw = "".join(c for c in self.code_var.get() if c.isdigit())[:6]
        self.code_var.set(raw)

    def _check_existing(self) -> None:
        creds = load_creds()
        if creds:
            self._status.set(f"Already connected as {creds.get('hostname')} — working in the background")
            self.connect_btn.config(text="Reconnect", state=tk.NORMAL)
            self._start_reporting(creds)

    def _apply_autostart(self) -> None:
        want = bool(self.autostart_var.get())
        save_config(self.server_var.get().strip().rstrip("/"), autostart=want)
        if want:
            exe = install_local_copy()
            if exe and enable_windows_autostart(exe):
                self._status.set(self._status.get() + " · Starts with Windows")
        else:
            disable_windows_autostart()

    def _on_connect(self) -> None:
        server = self.server_var.get().strip().rstrip("/")
        code = self.code_var.get().strip()
        if not server:
            messagebox.showerror("UITOP Agent", "Paste the UITOP address from the website.")
            return
        if len(code) != 6:
            messagebox.showerror("UITOP Agent", "Enter the 6-digit code from UITOP.")
            return
        self.connect_btn.config(state=tk.DISABLED)
        self._status.set("Connecting…")
        self.root.update_idletasks()
        try:
            creds = pair_agent(server, code)
            self._apply_autostart()
            self._status.set(f"Connected! {creds['hostname']} is linked to UITOP.")
            messagebox.showinfo(
                "UITOP Agent",
                f"Success!\n\nThis PC ({creds['hostname']}) is connected.\n\n"
                "You can minimize this window. It will keep working in the background.\n"
                + (
                    "It will also start when you sign in to Windows."
                    if self.autostart_var.get()
                    else ""
                ),
            )
            self._start_reporting(creds)
        except Exception as exc:  # noqa: BLE001
            self._status.set(str(exc))
            messagebox.showerror("UITOP Agent", str(exc))
        finally:
            self.connect_btn.config(state=tk.NORMAL)

    def _start_reporting(self, creds: dict) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._report_loop, args=(creds,), daemon=True)
        self._thread.start()

    def _report_loop(self, creds: dict) -> None:
        server = creds.get("server", DEFAULT_SERVER).rstrip("/")
        last_report = 0.0
        while not self._stop.is_set():
            try:
                access = agent_access_token(server, creds)
                now = time.time()
                if now - last_report >= REPORT_INTERVAL:
                    report_once(server, access)
                    last_report = now
                    self.root.after(
                        0,
                        lambda: self._status.set(f"Connected · {creds.get('hostname')}"),
                    )
                self._poll_commands(server, access, creds)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda e=exc: self._status.set(f"Waiting to reconnect… ({e})"))
            for _ in range(COMMAND_POLL_SECONDS):
                if self._stop.is_set():
                    break
                time.sleep(1)

    def _poll_commands(self, server: str, access: str, creds: dict) -> None:
        try:
            commands = http_json("GET", f"{server}/api/v1/agents/commands", token=access)
        except Exception:
            return
        if not isinstance(commands, list) or not commands:
            return
        for item in commands:
            if not isinstance(item, dict):
                continue
            cmd_id = item.get("id")
            command = item.get("command") or ""
            params = item.get("params") or {}
            try:
                result = execute_command(command, params)
                if result == "SYNC_INVENTORY":
                    report_once(server, access)
                    result = "Inventory sync completed"
                http_json(
                    "POST",
                    f"{server}/api/v1/agents/commands/{cmd_id}/result",
                    {"status": "completed", "result": result},
                    token=access,
                )
                self.root.after(
                    0,
                    lambda c=command, r=result: self._status.set(f"Ran {c}: {r}"),
                )
            except Exception as exc:  # noqa: BLE001
                try:
                    http_json(
                        "POST",
                        f"{server}/api/v1/agents/commands/{cmd_id}/result",
                        {"status": "failed", "result": str(exc)},
                        token=access,
                    )
                except Exception:
                    pass
                self.root.after(0, lambda e=exc: self._status.set(f"Command failed: {e}"))

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self) -> None:
        # Prefer minimize so reporting continues; ask only if they insist
        if messagebox.askyesno(
            "UITOP Agent",
            "Minimize to the taskbar and keep connected?\n\n"
            "Choose No to fully quit (this PC will stop reporting until you open the agent again).",
        ):
            self.root.iconify()
            return
        self._stop.set()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    start_minimized = "--minimized" in args or "--silent" in args
    try:
        import psutil  # noqa: F401
    except ImportError:
        if not getattr(sys, "frozen", False):
            messagebox.showerror("UITOP Agent", "Missing dependency: psutil")
            return 1
    app = AgentApp(start_minimized=start_minimized)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
