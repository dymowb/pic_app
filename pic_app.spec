# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for pic_app.

Build with:
    pyinstaller pic_app.spec
"""

import sys
from pathlib import Path

SRC = str(Path("src").resolve())

a = Analysis(
    ["src/main.py"],
    pathex=[SRC],                   # so 'from ui.xxx import ...' resolves
    binaries=[],
    datas=[
        ("assets", "assets"),       # bundle icons etc.
    ],
    hiddenimports=[
        # imagehash pulls in scipy optionally — include common ones
        "PIL._tkinter_finder",
        "cv2",
        "numpy",
        "imagehash",
        # PyQt6 plugins needed for Windows rendering
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pic_app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\icons\\app.ico",  # Windows path separator
)
