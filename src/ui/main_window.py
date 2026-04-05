"""
Main application window.

Full pipeline (Phases 1–5)
--------------------------
1. Open Folder → ScanWorker: thumbnails cached in GroupsView
2. scan_complete → HashWorker: pHash per image
3. hash_complete → cluster() → GroupsView.show_groups()
4. show_groups → AnalysisWorker: quality metrics per image
5. analysis_complete → score_group() per group → badges + recommendations
"""

from __future__ import annotations

import logging
from pathlib import Path

import imagehash

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from config import load_settings, save_settings
from analysis.clusterer import cluster
from analysis.scorer import score_group, ScoringWeights
from ui.groups_view import GroupsView
from ui.preview_panel import PreviewPanel
from workers.scan_worker import ScanWorker
from workers.hash_worker import HashWorker
from workers.analysis_worker import AnalysisWorker

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
        self._analysis_worker: AnalysisWorker | None = None
        self._scanned_paths: list[Path] = []
        self._all_cards: dict[str, object] = {}
        self._current_groups: list[list[Path]] = []
        self._metrics_store: dict[str, object] = {}
        # Watchdog: fires if hashing produces no progress for 30 s
        self._hash_watchdog = QTimer(self)
        self._hash_watchdog.setSingleShot(True)
        self._hash_watchdog.setInterval(30_000)
        self._hash_watchdog.timeout.connect(self._on_hash_watchdog)
        self._last_hash_progress = 0

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
        if dialog.exec():
            # Settings were saved — re-score with new weights if we have results
            if self._current_groups and self._metrics_store:
                self._run_scoring()

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
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.cancel()
            self._analysis_worker.wait()
        self._all_cards.clear()

        self._scanned_paths.clear()
        self._current_groups.clear()
        self._metrics_store.clear()
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
        self._progress.setVisible(True)
        self._groups_view.show_banner(
            f"Computing similarity fingerprints for {len(self._scanned_paths)} images…"
        )

        self._last_hash_progress = 0
        self._hash_watchdog.start()  # 30 s watchdog

        self._hash_worker = HashWorker(self._scanned_paths, parent=self)
        self._hash_worker.progress.connect(self._on_hash_progress)
        self._hash_worker.hash_complete.connect(self._on_hash_complete)
        self._hash_worker.error.connect(self._on_hash_error)
        self._hash_worker.start()

    def _on_hash_progress(self, current: int, total: int) -> None:
        self._last_hash_progress = current
        self._hash_watchdog.start()   # reset watchdog on each tick
        if total > 0:
            self._progress.setValue(int(current / total * 100))
            self._progress.setFormat(f"Hashing {current}/{total}")

    def _on_hash_error(self, path: str, message: str) -> None:
        logger.warning("Hash error %s: %s", path, message)

    def _on_hash_watchdog(self) -> None:
        """Fires if no hash progress signal arrives within 30 s."""
        if self._hash_worker and self._hash_worker.isRunning():
            self._hash_worker.cancel()
            self._hash_worker.wait(3000)

        self._progress.setVisible(False)
        self._open_action.setEnabled(True)
        n = len(self._scanned_paths)
        stuck_at = self._last_hash_progress
        QMessageBox.warning(
            self,
            "Hashing Stalled",
            f"The similarity hashing stopped responding after {stuck_at}/{n} images.\n\n"
            "This usually means one image file is in an unusual format or is very large.\n\n"
            "The app will try to continue with the images that were processed.\n"
            "If this keeps happening, remove the problematic file and try again.",
        )
        # Fall through with whatever partial hashes exist (none in this path)
        self._groups_view.show_banner(
            "Hashing was interrupted. Open a folder to try again."
        )

    def _on_hash_complete(self, raw_hashes: dict) -> None:
        self._hash_watchdog.stop()
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

        self._current_groups = groups
        self._groups_view.show_groups(groups, unique)

        # Phase 4: start quality analysis on all grouped + unique paths
        all_paths = [p for g in groups for p in g] + unique
        if all_paths:
            self._start_analysis(all_paths)

    # ------------------------------------------------------------------
    # Phase 3: Quality Analysis
    # ------------------------------------------------------------------

    def _start_analysis(self, paths: list[Path]) -> None:
        self._progress.setValue(0)
        self._progress.setFormat("Analysing quality…")
        self._progress.setVisible(True)
        self.statusBar().showMessage(
            f"Analysing image quality for {len(paths)} image(s)…"
        )

        self._analysis_worker = AnalysisWorker(paths, parent=self)
        self._analysis_worker.metrics_ready.connect(self._on_metrics_ready)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.analysis_complete.connect(self._on_analysis_complete)
        self._analysis_worker.error.connect(
            lambda p, m: logger.warning("Analysis error %s: %s", p, m)
        )
        self._analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(current / total * 100))
            self._progress.setFormat(f"Analysing {current}/{total}")

    def _on_metrics_ready(self, path_str: str, metrics) -> None:
        self._groups_view.set_card_metrics(path_str, metrics)
        self._metrics_store[path_str] = metrics

    def _on_analysis_complete(self) -> None:
        self._progress.setVisible(False)
        self._run_scoring()

    # ------------------------------------------------------------------
    # Phase 5: Scoring
    # ------------------------------------------------------------------

    def _run_scoring(self) -> None:
        settings = load_settings()
        w = settings.get("weights", {})
        try:
            weights = ScoringWeights.from_percent(
                sharpness=w.get("sharpness", 50),
                exposure=w.get("exposure", 30),
                resolution=w.get("resolution", 20),
            )
        except ValueError:
            weights = ScoringWeights()

        for idx, group in enumerate(self._current_groups):
            group_metrics = {
                p: self._metrics_store[str(p)]
                for p in group
                if str(p) in self._metrics_store
            }
            if not group_metrics:
                continue
            self._groups_view.store_group_metrics(idx, group_metrics)
            scores = score_group(group_metrics, weights)
            self._groups_view.apply_group_scores(idx, scores)

        if self._current_groups:
            self._apply_action.setEnabled(True)
            self.statusBar().showMessage(
                "Ready. Recommendations applied — hover images for quality metrics."
            )
        else:
            self.statusBar().showMessage(
                "Analysis complete. Hover any image to see quality metrics."
            )

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
