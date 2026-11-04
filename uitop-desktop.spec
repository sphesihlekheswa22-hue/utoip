# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for UITOP Desktop."""
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

datas = [
    (str(root / "templates"), "templates"),
    (str(root / "static"), "static"),
    (str(root / "migrations"), "migrations"),
    (str(root / "agents"), "agents"),
]

hiddenimports = [
    "uitop",
    "uitop.models",
    "uitop.models.auth",
    "uitop.models.inventory",
    "uitop.models.files",
    "uitop.models.helpdesk",
    "uitop.models.maintenance",
    "uitop.models.security",
    "uitop.models.settings",
    "routes",
    "routes.auth",
    "routes.discovery",
    "routes.computers",
    "routes.servers",
    "routes.network",
    "routes.printers",
    "engineio.async_drivers.threading",
    "webview",
    "clr_loader",
]

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UITOP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="UITOP",
)
