"""
Main application window.

Phase 3 flow
------------
1. User clicks "Open Folder"
2. ScanWorker runs → thumbnails arrive live, cached in GroupsView
3. On scan_complete → HashWorker runs → pHash per image
4. On hash_complete → cluster() → GroupsView.show_groups()
"""

from __future__ import annotations

import logging
from pathlib import Path

import imagehash

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from config import load_settings, save_settings
from analysis.clusterer import cluster
from ui.groups_view import GroupsView
from ui.preview_panel import PreviewPanel
from workers.scan_worker import ScanWorker
from workers.hash_worker import HashWorker

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
        self._hash_worker: HashWorker | None = None
        self._scanned_paths: list[Path] = []

        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()

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

        self._open_action = QAction("📂  Open Folder", self)
        self._open_action.setStatusTip("Select a folder to scan for duplicate photos")
        self._open_action.triggered.connect(self._on_open_folder)
        toolbar.addAction(self._open_action)

        toolbar.addSeparator()

        self._apply_action = QAction("✅  Apply Recommendations", self)
        self._apply_action.setStatusTip(
            "Mark all non-recommended images for deletion across all groups"
        )
        self._apply_action.setEnabled(False)
        toolbar.addAction(self._apply_action)

        toolbar.addSeparator()

        settings_action = QAction("⚙️  Settings", self)
        settings_action.setStatusTip("Configure similarity threshold and scoring weights")
        settings_action.triggered.connect(self._on_open_settings)
        toolbar.addAction(settings_action)

    def _build_central_widget(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self._groups_view = GroupsView(self._splitter)
        self._groups_view.image_selected.connect(self._on_image_selected)
        self._splitter.addWidget(self._groups_view)

        self._preview = PreviewPanel(self._splitter)
        self._splitter.addWidget(self._preview)

        self._splitter.setSizes([860, 420])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)

        self.setCentralWidget(self._splitter)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(240)
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        status_bar.addWidget(self._progress)

        self._status_images = QLabel("Images: —")
        self._status_groups = QLabel("Groups: —")
        self._status_space = QLabel("Space reclaimable: —")

        for lbl in (self._status_images, self._status_groups, self._status_space):
            lbl.setStyleSheet("padding: 0 12px;")
            status_bar.addPermanentWidget(lbl)

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
        settings = load_settings()
        settings["last_folder"] = str(self._current_folder)
        save_settings(settings)
        self._start_scan()

    def _on_open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Phase 1: Scan
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        assert self._current_folder is not None

        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait()
        if self._hash_worker and self._hash_worker.isRunning():
            self._hash_worker.cancel()
            self._hash_worker.wait()

        self._scanned_paths.clear()
        self._apply_action.setEnabled(False)
        self._groups_view.show_banner("Scanning folder…")
        self._preview.clear()

        self._progress.setValue(0)
        self._progress.setFormat("Scanning…")
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
        self._scan_worker.error.connect(lambda p, m: logger.warning("Skip %s: %s", p, m))
        self._scan_worker.start()

    def _on_file_ready(
        self, path: str, qimage: QImage, file_size: int, img_w: int, img_h: int
    ) -> None:
        pixmap = QPixmap.fromImage(qimage)
        self._groups_view.cache_image(path, pixmap, file_size, img_w, img_h)
        self._scanned_paths.append(Path(path))
        self._status_images.setText(f"Images: {len(self._scanned_paths)}")

    def _on_scan_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(current / total * 100))
            self._progress.setFormat(f"Scanning {current}/{total}")

    def _on_scan_complete(self, total: int) -> None:
        if total == 0:
            self._progress.setVisible(False)
            self._open_action.setEnabled(True)
            self._groups_view.show_banner("No supported images found in the selected folder.")
            self.statusBar().showMessage("Scan complete — no images found.")
            return

        self.statusBar().showMessage(f"Scan complete ({total} images). Computing similarity hashes…")
        self._start_hashing()

    # ------------------------------------------------------------------
    # Phase 2: Hash
    # ------------------------------------------------------------------

    def _start_hashing(self) -> None:
        self._progress.setValue(0)
        self._progress.setFormat("Hashing…")
        self._groups_view.show_banner(
            f"Computing similarity fingerprints for {len(self._scanned_paths)} images…"
        )

        self._hash_worker = HashWorker(self._scanned_paths, parent=self)
        self._hash_worker.progress.connect(self._on_hash_progress)
        self._hash_worker.hash_complete.connect(self._on_hash_complete)
        self._hash_worker.error.connect(lambda p, m: logger.warning("Hash error %s: %s", p, m))
        self._hash_worker.start()

    def _on_hash_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(current / total * 100))
            self._progress.setFormat(f"Hashing {current}/{total}")

    def _on_hash_complete(self, raw_hashes: dict) -> None:
        # raw_hashes: dict[str, str]  path → hex hash string
        self._progress.setVisible(False)
        self._open_action.setEnabled(True)

        # Reconstruct imagehash objects and key by Path
        hashes: dict[Path, imagehash.ImageHash] = {}
        for path_str, hex_str in raw_hashes.items():
            try:
                hashes[Path(path_str)] = imagehash.hex_to_hash(hex_str)
            except Exception as exc:
                logger.warning("Bad hash for %s: %s", path_str, exc)

        if not hashes:
            self._groups_view.show_banner("Could not hash any images.")
            return

        # Cluster — fast enough to run on main thread for ≤ 500 images
        settings = load_settings()
        threshold = settings.get("similarity_threshold", 10)
        groups, unique = cluster(hashes, threshold=threshold)

        # Update status bar
        total_dups = sum(len(g) for g in groups) - len(groups)
        space_mb = self._estimate_space_mb(groups)
        self._status_groups.setText(f"Groups: {len(groups)}")
        self._status_space.setText(f"Space reclaimable: ≈{space_mb:.1f} MB")
        self.statusBar().showMessage(
            f"Done — {len(groups)} duplicate group(s), "
            f"{total_dups} redundant image(s), "
            f"{len(unique)} unique."
        )

        self._groups_view.show_groups(groups, unique)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _estimate_space_mb(self, groups: list[list[Path]]) -> float:
        """Sum file sizes of all non-first images in each group (rough estimate)."""
        total = 0
        for group in groups:
            for path in group[1:]:
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return total / (1024 * 1024)

    def _on_image_selected(self, path: str) -> None:
        self._preview.set_image(path)

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
