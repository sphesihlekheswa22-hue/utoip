"""
UITOP Desktop — runs the Flask server and opens a native Windows window.

Usage (from project root, venv active):

  python desktop_app.py

Build a Windows .exe (optional):

  powershell -File tools/build_desktop.ps1
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is on sys.path when frozen or run as script
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if getattr(sys, "frozen", False):
    # PyInstaller: also keep a writable base next to the exe for instance/
    BUNDLE_ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent
    APP_DIR = BUNDLE_ROOT

if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

HOST = os.getenv("UITOP_HOST", "0.0.0.0")
PORT = int(os.getenv("UITOP_PORT", "5500"))
WINDOW_URL = f"http://127.0.0.1:{PORT}"


def _prepare_runtime_paths() -> None:
    """Point instance/DB next to the .exe when frozen so data persists."""
    instance = APP_DIR / "instance"
    instance.mkdir(parents=True, exist_ok=True)
    db_path = instance / "uitop.db"
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    os.environ.setdefault("FILES_ROOT", str(instance / "repo_files"))
    # Desktop builds should not use Flask debug reloader
    os.environ.setdefault("FLASK_ENV", "production")


def _wait_for_server(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _run_flask() -> None:
    from uitop import create_app

    # When frozen, templates/static live under _MEIPASS
    app = create_app(os.getenv("FLASK_ENV", "production"))
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)


def main() -> int:
    _prepare_runtime_paths()

    server = threading.Thread(target=_run_flask, name="uitop-flask", daemon=True)
    server.start()

    if not _wait_for_server():
        print(f"UITOP failed to start on port {PORT}.")
        return 1

    lan = _lan_ip()
    print(f"UITOP Desktop running")
    print(f"  Local:  {WINDOW_URL}")
    print(f"  LAN:    http://{lan}:{PORT}  (agents on other PCs use this)")
    print("Close the window to stop the server.")

    try:
        import webview

        webview.create_window(
            "Umzinyathi IT Operations Platform",
            WINDOW_URL,
            width=1440,
            height=920,
            min_size=(1024, 700),
        )
        webview.start()
    except ImportError:
        print("pywebview not installed — opening your default browser instead.")
        print("Install with:  pip install pywebview")
        webbrowser.open(WINDOW_URL)
        try:
            while server.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
