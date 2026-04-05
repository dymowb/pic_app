"""
ScanWorker — background QThread that drives analysis.scanner and emits
per-file results as Qt signals so the UI can update live.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from analysis.scanner import enumerate_images, load_image_info

logger = logging.getLogger(__name__)


def _pil_rgba_to_qimage(pil_img) -> QImage:
    """Convert a Pillow RGBA image to a QImage (detached from PIL buffer)."""
    data = pil_img.tobytes("raw", "RGBA")
    return QImage(
        data,
        pil_img.width,
        pil_img.height,
        pil_img.width * 4,
        QImage.Format.Format_RGBA8888,
    ).copy()


class ScanWorker(QThread):
    """
    Signals
    -------
    file_ready(path_str, QImage, file_size, img_width, img_height)
    progress(current, total)
    scan_complete(total_processed)
    error(path_str, message)
    """

    file_ready = pyqtSignal(str, QImage, int, int, int)
    progress = pyqtSignal(int, int)
    scan_complete = pyqtSignal(int)
    error = pyqtSignal(str, str)

    def __init__(self, folder: Path, parent=None) -> None:
        super().__init__(parent)
        self._folder = folder
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        paths = enumerate_images(self._folder)
        total = len(paths)
        processed = 0

        for path in paths:
            if self._cancelled:
                break
            try:
                info = load_image_info(path)
                qimage = _pil_rgba_to_qimage(info.thumb)
                self.file_ready.emit(
                    str(info.path), qimage, info.file_size, info.orig_width, info.orig_height
                )
            except Exception as exc:
                logger.warning("Skipping %s: %s", path, exc)
                self.error.emit(str(path), str(exc))

            processed += 1
            self.progress.emit(processed, total)

        self.scan_complete.emit(processed)
