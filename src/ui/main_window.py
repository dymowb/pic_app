"""
Main application window.

Layout
------
┌─────────────────────────────────────────┐
│  Toolbar: [Open Folder] [Apply Recs]    │
├──────────────────────────┬──────────────┤
│                          │              │
│   Scroll area            │   Preview    │
│   (thumbnail groups)     │   panel      │
│                          │              │
├──────────────────────────┴──────────────┤
│  Status bar: groups | duplicates | MB   │
└─────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class _PlaceholderWidget(QWidget):
    """Temporary placeholder used until real widgets are implemented in later phases."""

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(label)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("pic_app — Duplicate Photo Finder")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        self._current_folder: Path | None = None

        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Open Folder
        open_action = QAction("Open Folder", self)
        open_action.setStatusTip("Select a folder to scan for duplicate photos")
        open_action.triggered.connect(self._on_open_folder)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # Apply Recommendations (disabled until analysis is done)
        self._apply_action = QAction("Apply Recommendations", self)
        self._apply_action.setStatusTip(
            "Mark all non-recommended images for deletion across all groups"
        )
        self._apply_action.setEnabled(False)
        toolbar.addAction(self._apply_action)

        toolbar.addSeparator()

        # Settings
        settings_action = QAction("Settings", self)
        settings_action.setStatusTip("Configure similarity threshold and scoring weights")
        settings_action.triggered.connect(self._on_open_settings)
        toolbar.addAction(settings_action)

    def _build_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: scrollable area for thumbnail groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._groups_container = _PlaceholderWidget(
            "Open a folder to start scanning for duplicate photos."
        )
        scroll.setWidget(self._groups_container)
        splitter.addWidget(scroll)

        # Right: image preview panel
        self._preview_panel = _PlaceholderWidget("Select an image to preview it here.")
        splitter.addWidget(self._preview_panel)

        splitter.setSizes([860, 420])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        self.setCentralWidget(splitter)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self._status_groups = QLabel("Groups: —")
        self._status_duplicates = QLabel("Duplicates: —")
        self._status_space = QLabel("Space reclaimable: —")

        for label in (self._status_groups, self._status_duplicates, self._status_space):
            label.setStyleSheet("padding: 0 12px;")
            status_bar.addPermanentWidget(label)

        status_bar.showMessage("Ready. Open a folder to begin.")

    # ------------------------------------------------------------------
    # Slots
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
        self.statusBar().showMessage(f"Scanning: {self._current_folder} …")
        # Phase 2 will wire a ScanWorker here.

    def _on_open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.exec()

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
        if duplicates is not None:
            self._status_duplicates.setText(f"Duplicates: {duplicates}")
        if space_mb is not None:
            self._status_space.setText(f"Space reclaimable: {space_mb:.1f} MB")
