"""
AnalysisWorker — background QThread that computes quality metrics
for every image path provided and emits results per image.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from analysis.quality import compute_metrics, ImageMetrics

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """
    Signals
    -------
    metrics_ready(path_str, ImageMetrics)
        Emitted for each successfully analysed image.
    progress(current, total)
    analysis_complete()
    error(path_str, message)
    """

    metrics_ready = pyqtSignal(str, object)   # (path, ImageMetrics)
    progress = pyqtSignal(int, int)
    analysis_complete = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self, paths: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._paths)
        for i, path in enumerate(self._paths):
            if self._cancelled:
                break
            try:
                metrics = compute_metrics(path)
                self.metrics_ready.emit(str(path), metrics)
            except Exception as exc:
                logger.warning("Analysis failed for %s: %s", path, exc)
                self.error.emit(str(path), str(exc))
            self.progress.emit(i + 1, total)

        self.analysis_complete.emit()
