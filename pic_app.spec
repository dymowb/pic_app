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
        # --- imagehash and its internals ---
        "imagehash",
        # --- numpy modules imagehash uses for DCT-based pHash ---
        "numpy",
        "numpy.fft",
        "numpy.fft.fftpack",
        "numpy.core._multiarray_umath",
        "numpy.core.multiarray",
        # --- Pillow format plugins (ensures all image types open) ---
        "PIL._tkinter_finder",
        "PIL.JpegImagePlugin",
        "PIL.PngImagePlugin",
        "PIL.BmpImagePlugin",
        "PIL.WebPImagePlugin",
        "PIL.TiffImagePlugin",
        "PIL.GifImagePlugin",
        # --- OpenCV ---
        "cv2",
        # --- PyQt6 ---
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "IPython",
        "notebook",
        "scipy",      # not needed; numpy handles DCT natively
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
