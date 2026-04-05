"""
Main application window.

Layout
------
┌─────────────────────────────────────────┐
│  Toolbar: [Open Folder] [Apply Recs]    │
├──────────────────────────┬──────────────┤
│                          │              │
│   ThumbnailGrid          │  PreviewPanel│
│   (scrollable cards)     │              │
│                          │              │
├──────────────────────────┴──────────────┤
│  Progress bar (hidden when idle)        │
│  Status bar: images | groups | space    │
└─────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QImage
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from config import load_settings, save_settings
from ui.preview_panel import PreviewPanel
from ui.thumbnail_grid import ThumbnailGrid
from workers.scan_worker import ScanWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("pic_app — Duplicate Photo Finder")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        self._current_folder: Path | None = None
        self._scan_worker: ScanWorker | None = None
        self._total_images = 0

        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()

        # Restore last folder from settings
        settings = load_settings()
        if settings.get("last_folder"):
            self._current_folder = Path(settings["last_folder"])

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 6px; padding: 4px; }")
        self.addToolBar(toolbar)

        # Open Folder
        self._open_action = QAction("📂  Open Folder", self)
        self._open_action.setStatusTip("Select a folder to scan for duplicate photos")
        self._open_action.triggered.connect(self._on_open_folder)
        toolbar.addAction(self._open_action)

        toolbar.addSeparator()

        # Apply Recommendations (enabled in Phase 5)
        self._apply_action = QAction("✅  Apply Recommendations", self)
        self._apply_action.setStatusTip(
            "Mark all non-recommended images for deletion across all groups"
        )
        self._apply_action.setEnabled(False)
        toolbar.addAction(self._apply_action)

        toolbar.addSeparator()

        # Settings
        settings_action = QAction("⚙️  Settings", self)
        settings_action.setStatusTip("Configure similarity threshold and scoring weights")
        settings_action.triggered.connect(self._on_open_settings)
        toolbar.addAction(settings_action)

    def _build_central_widget(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: thumbnail grid
        self._grid = ThumbnailGrid(self._splitter)
        self._grid.image_selected.connect(self._on_image_selected)
        self._grid.show_empty_message("Open a folder to start scanning for duplicate photos.")
        self._splitter.addWidget(self._grid)

        # Right: preview panel
        self._preview = PreviewPanel(self._splitter)
        self._splitter.addWidget(self._preview)

        self._splitter.setSizes([860, 420])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)

        self.setCentralWidget(self._splitter)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        # Progress bar (hidden when idle)
        self._progress = QProgressBar()
        self._progress.setFixedWidth(220)
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        status_bar.addWidget(self._progress)

        # Permanent stat labels (right side)
        self._status_images = QLabel("Images: —")
        self._status_groups = QLabel("Groups: —")
        self._status_space = QLabel("Space reclaimable: —")

        for label in (self._status_images, self._status_groups, self._status_space):
            label.setStyleSheet("padding: 0 12px;")
            status_bar.addPermanentWidget(label)

        status_bar.showMessage("Ready. Open a folder to begin.")

    # ------------------------------------------------------------------
    # Toolbar slots
    # ------------------------------------------------------------------

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Photo Folder",
            str(self._current_folder or Path.home()),
        )
        if not folder:
            return

        self._current_folder = Path(folder)

        # Persist last folder
        settings = load_settings()
        settings["last_folder"] = str(self._current_folder)
        save_settings(settings)

        self._start_scan()

    def _on_open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Scan workflow
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        assert self._current_folder is not None

        # Cancel any in-progress scan
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait()

        self._grid.clear()
        self._preview.clear()
        self._total_images = 0
        self._apply_action.setEnabled(False)

        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._status_images.setText("Images: scanning…")
        self._status_groups.setText("Groups: —")
        self._status_space.setText("Space reclaimable: —")
        self.statusBar().showMessage(f"Scanning  {self._current_folder} …")
        self._open_action.setEnabled(False)

        self._scan_worker = ScanWorker(self._current_folder, parent=self)
        self._scan_worker.file_ready.connect(self._on_file_ready)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    # ------------------------------------------------------------------
    # Worker signal handlers (called on main thread via Qt queued connection)
    # ------------------------------------------------------------------

    def _on_file_ready(
        self, path: str, qimage: QImage, file_size: int, img_w: int, img_h: int
    ) -> None:
        self._grid.add_image(path, qimage, file_size, img_w, img_h)
        self._total_images += 1
        self._status_images.setText(f"Images: {self._total_images}")

    def _on_scan_progress(self, current: int, total: int) -> None:
        if total > 0:
            pct = int(current / total * 100)
            self._progress.setValue(pct)
            self._progress.setFormat(f"{current} / {total}")

    def _on_scan_complete(self, total: int) -> None:
        self._progress.setVisible(False)
        self._open_action.setEnabled(True)

        if total == 0:
            self._grid.show_empty_message(
                "No supported images found in the selected folder."
            )
            self.statusBar().showMessage("Scan complete — no images found.")
        else:
            self.statusBar().showMessage(
                f"Scan complete — {total} image(s) loaded. "
                "Grouping analysis coming in Phase 3."
            )
            self._status_images.setText(f"Images: {total}")

    def _on_scan_error(self, path: str, message: str) -> None:
        logger.warning("Skipped file %s: %s", path, message)

    # ------------------------------------------------------------------
    # Grid → preview bridge
    # ------------------------------------------------------------------

    def _on_image_selected(self, path: str) -> None:
        self._preview.set_image(path)

    # ------------------------------------------------------------------
    # Public helpers (used by workers in later phases)
    # ------------------------------------------------------------------

    def update_status(
        self,
        groups: int | None = None,
        duplicates: int | None = None,
        space_mb: float | None = None,
    ) -> None:
        if groups is not None:
            self._status_groups.setText(f"Groups: {groups}")
        if space_mb is not None:
            self._status_space.setText(f"Space reclaimable: {space_mb:.1f} MB")
