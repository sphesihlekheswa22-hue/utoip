# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for UITOP Agent (standalone, no Python needed on target PC)."""
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

hiddenimports = ["psutil", "tkinter", "tkinter.ttk", "command_exec"]

a = Analysis(
    ["agents/uitop_agent_gui.py"],
    pathex=[str(root), str(root / "agents")],
    binaries=[],
    datas=[(str(root / "agents" / "command_exec.py"), ".")],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="UITOP-Agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
