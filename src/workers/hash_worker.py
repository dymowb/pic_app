"""
HashWorker — background QThread that computes pHash for a list of image paths
and emits results for the main thread to cluster.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from analysis.hasher import compute_phash

logger = logging.getLogger(__name__)


class HashWorker(QThread):
    """
    Signals
    -------
    progress(current, total)
        Emitted after each file is hashed.
    hash_complete(hashes)
        Emitted when all files are processed.
        hashes is a dict[str, str] mapping path string → pHash hex string.
    error(path_str, message)
        Emitted when a single file fails to hash; worker continues.
    """

    progress = pyqtSignal(int, int)
    hash_complete = pyqtSignal(object)   # dict[str, str]
    error = pyqtSignal(str, str)

    def __init__(self, paths: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._paths)
        hashes: dict[str, str] = {}

        for i, path in enumerate(self._paths):
            if self._cancelled:
                break
            try:
                h = compute_phash(path)
                hashes[str(path)] = str(h)  # hex string, e.g. "f8e0c0a0b0d0e0f0"
            except Exception as exc:
                logger.warning("Could not hash %s: %s", path, exc)
                self.error.emit(str(path), str(exc))

            self.progress.emit(i + 1, total)

        self.hash_complete.emit(hashes)
