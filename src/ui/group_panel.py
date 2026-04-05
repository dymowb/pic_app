"""
GroupPanel — a horizontal strip showing all images in one duplicate group.

Layout per panel
----------------
┌─────────────────────────────────────────────────────┐
│  Group 1  (4 images)                         [▼]   │  ← header bar
├─────────────────────────────────────────────────────┤
│  [card] [card] [card] [card]                        │  ← horizontal scroll
└─────────────────────────��───────────────────────────┘

Badges (Best / Runner-up) are set by the scoring engine in Phase 5.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.image_card import ImageCard, CARD_WIDTH, CARD_HEIGHT


class GroupPanel(QFrame):
    """
    Visual strip for one duplicate group.

    Parameters
    ----------
    group_index  : 1-based display number
    image_data   : list of (path_str, QPixmap, file_size, img_w, img_h)

    Signals
    -------
    image_selected(path)  — bubbled up from any card click
    """

    image_selected = pyqtSignal(str)

    def __init__(
        self,
        group_index: int,
        image_data: list[tuple[str, QPixmap, int, int, int]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._cards: dict[str, ImageCard] = {}
        self._selected_path: str | None = None
        self._group_index = group_index
        self._image_data = image_data

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(4)

        # Header bar
        header = self._make_header()
        outer.addWidget(header)

        # Horizontal scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFixedHeight(CARD_HEIGHT + 12)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(4, 4, 4, 4)
        cards_layout.setSpacing(8)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for path_str, pixmap, file_size, img_w, img_h in self._image_data:
            card = ImageCard(path_str, pixmap, file_size, img_w, img_h, cards_widget)
            card.clicked.connect(self._on_card_clicked)
            cards_layout.addWidget(card)
            self._cards[path_str] = card

        cards_layout.addStretch()
        scroll.setWidget(cards_widget)
        outer.addWidget(scroll)

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setStyleSheet(
            "background: #e8eaf6; border-radius: 4px; padding: 2px 6px;"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel(
            f"Group {self._group_index}  —  {len(self._image_data)} similar images"
        )
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        title.setFont(font)
        layout.addWidget(title)
        layout.addStretch()

        # Total size of the group
        total_bytes = sum(sz for _, _, sz, _, _ in self._image_data)
        size_label = QLabel(_human_size(total_bytes))
        size_label.setStyleSheet("color: #555; font-size: 9px;")
        layout.addWidget(size_label)

        return header

    # ------------------------------------------------------------------
    # Public API (called by Phase 5 scorer)
    # ------------------------------------------------------------------

    def set_badge(self, path: str, badge: int) -> None:
        """Apply a badge (BADGE_BEST / BADGE_RUNNER_UP) to a specific card."""
        if path in self._cards:
            self._cards[path].set_badge(badge)

    def set_recommendation_reason(self, path: str, reason: str) -> None:
        """Set tooltip reason text on a card (Phase 5)."""
        if path in self._cards:
            self._cards[path].setToolTip(reason)

    def card_paths(self) -> list[str]:
        return list(self._cards.keys())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_card_clicked(self, path: str) -> None:
        if self._selected_path and self._selected_path in self._cards:
            self._cards[self._selected_path].set_selected(False)
        self._selected_path = path
        self._cards[path].set_selected(True)
        self.image_selected.emit(path)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.0f} TB"
