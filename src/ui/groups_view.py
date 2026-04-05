"""
GroupsView — the main left-panel content widget for Phase 3+.

Shows:
  1. A vertical list of GroupPanel strips (duplicate groups, largest first)
  2. A collapsible "Unique Images" section at the bottom (no duplicates found)
  3. A status banner ("Hashing…", "No duplicates found", etc.)
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.group_panel import GroupPanel
from ui.image_card import CARD_HEIGHT, CARD_WIDTH, ImageCard


class _CollapsibleSection(QWidget):
    """A titled section that can be expanded / collapsed."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        header = QWidget()
        header.setStyleSheet("background: #f5f5f5; border-radius: 4px;")
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(8, 4, 8, 4)

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(22, 22)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self._toggle)
        hrow.addWidget(self._toggle_btn)

        lbl = QLabel(title)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        lbl.setFont(font)
        hrow.addWidget(lbl)
        hrow.addStretch()
        outer.addWidget(header)

        # Content container
        self._content = QWidget()
        self._content_layout = QHBoxLayout(self._content)
        self._content_layout.setContentsMargins(4, 4, 4, 4)
        self._content_layout.setSpacing(8)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        outer.addWidget(self._content)

    def add_widget(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "▶")


class GroupsView(QScrollArea):
    """
    Scrollable area showing GroupPanels + a unique images section.

    Signals
    -------
    image_selected(path)
    """

    image_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._group_panels: list[GroupPanel] = []
        self._pixmap_cache: dict[str, tuple[QPixmap, int, int, int]] = {}
        self._unique_cards: dict[str, "ImageCard"] = {}
        # Metrics stored per group index for re-scoring when weights change
        self._group_metrics: list[dict] = []   # list[dict[Path, ImageMetrics]]

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._container)

        self._show_banner("Open a folder to start scanning for duplicate photos.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cache_image(
        self, path: str, pixmap: QPixmap, file_size: int, img_w: int, img_h: int
    ) -> None:
        """Store pixmap + metadata so GroupPanels can be built from it."""
        self._pixmap_cache[path] = (pixmap, file_size, img_w, img_h)

    def show_banner(self, message: str) -> None:
        self._clear_layout()
        self._show_banner(message)

    def show_groups(
        self,
        groups: list[list[Path]],
        unique: list[Path],
    ) -> None:
        """
        Render GroupPanels for all duplicate groups and a unique section.

        Parameters
        ----------
        groups  : list of groups (each ≥ 2 paths), sorted by size desc
        unique  : paths that have no near-duplicates
        """
        self._clear_layout()
        self._group_panels.clear()
        self._unique_cards.clear()
        self._group_metrics.clear()

        if not groups and not unique:
            self._show_banner("No images found.")
            return

        if not groups:
            self._show_banner(
                f"No duplicate groups found.  "
                f"{len(unique)} unique image(s) shown below."
            )
        else:
            # Summary banner
            dup_count = sum(len(g) for g in groups) - len(groups)
            banner = _Banner(
                f"Found {len(groups)} duplicate group(s) — "
                f"{dup_count} image(s) can potentially be removed."
            )
            self._layout.addWidget(banner)

            # One GroupPanel per group
            for idx, group in enumerate(groups, start=1):
                image_data = self._build_image_data(group)
                if not image_data:
                    continue
                panel = GroupPanel(idx, image_data, self._container)
                panel.image_selected.connect(self.image_selected)
                self._layout.addWidget(panel)
                self._group_panels.append(panel)

        # Unique images section
        if unique:
            unique_data = self._build_image_data(unique)
            if unique_data:
                section = _CollapsibleSection(
                    f"Unique images  ({len(unique_data)} — no duplicates found)"
                )
                for path_str, pixmap, file_size, img_w, img_h in unique_data:
                    card = ImageCard(
                        path_str, pixmap, file_size, img_w, img_h, section
                    )
                    card.clicked.connect(self.image_selected)
                    section.add_widget(card)
                    self._unique_cards[path_str] = card
                self._layout.addWidget(section)

        self._layout.addStretch()

    def group_panels(self) -> list[GroupPanel]:
        return list(self._group_panels)

    def set_card_metrics(self, path: str, metrics) -> None:
        """Route quality metrics to the matching ImageCard (group or unique)."""
        for panel in self._group_panels:
            if path in panel._cards:
                panel._cards[path].set_metrics(metrics)
                return
        if path in self._unique_cards:
            self._unique_cards[path].set_metrics(metrics)

    def store_group_metrics(self, group_idx: int, metrics: dict) -> None:
        """Store metrics dict for a group so it can be re-scored when weights change."""
        while len(self._group_metrics) <= group_idx:
            self._group_metrics.append({})
        self._group_metrics[group_idx] = metrics

    def apply_group_scores(self, group_idx: int, scores: list) -> None:
        """Apply a scored list to the GroupPanel at group_idx."""
        if 0 <= group_idx < len(self._group_panels):
            self._group_panels[group_idx].apply_scores(scores)

    def rescore_all(self, weights) -> None:
        """Re-score all groups with new weights (called when settings change)."""
        from analysis.scorer import score_group
        for idx, panel in enumerate(self._group_panels):
            if idx < len(self._group_metrics) and self._group_metrics[idx]:
                scores = score_group(self._group_metrics[idx], weights)
                panel.apply_scores(scores)

    def get_keep_paths(self) -> list[str]:
        """Return the chosen keep path for every group (recommendation or override)."""
        return [
            p for panel in self._group_panels
            if (p := panel.get_keep_path()) is not None
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_image_data(
        self, paths: list[Path]
    ) -> list[tuple[str, QPixmap, int, int, int]]:
        result = []
        for p in paths:
            key = str(p)
            if key in self._pixmap_cache:
                pixmap, file_size, img_w, img_h = self._pixmap_cache[key]
                result.append((key, pixmap, file_size, img_w, img_h))
        return result

    def _clear_layout(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_banner(self, text: str) -> None:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        self._layout.addWidget(label)


class _Banner(QFrame):
    """Informational strip shown above the group list."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #e3f2fd; border: 1px solid #90caf9; border-radius: 6px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        layout.addWidget(label)
