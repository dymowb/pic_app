"""
Application configuration — pure Python, no Qt dependency.
Provides default settings, load, and save functions.
Config file location: %APPDATA%\\pic_app\\settings.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS: dict = {
    "similarity_threshold": 10,
    "weights": {
        "sharpness": 50,
        "exposure": 30,
        "resolution": 20,
    },
    "show_unique": True,
    "last_folder": "",
}


def config_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    config_dir = Path(appdata) / "pic_app"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_settings() -> dict:
    path = config_path()
    if path.exists():
        try:
            with path.open() as f:
                stored = json.load(f)
            merged = dict(DEFAULTS)
            merged.update(stored)
            merged["weights"] = dict(DEFAULTS["weights"])
            merged["weights"].update(stored.get("weights", {}))
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    with config_path().open("w") as f:
        json.dump(settings, f, indent=2)
