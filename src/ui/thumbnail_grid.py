"""
ThumbnailGrid — a responsive, scrollable grid of ImageCard widgets.

All images are shown in a flat grid for Phase 2.
Phase 3 will replace this with grouped panels (GroupPanel strips).
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ui.image_card import CARD_WIDTH, ImageCard


class ThumbnailGrid(QScrollArea):
    """
    Scrollable grid of ImageCard widgets.

    Signals
    -------
    image_selected(path)  — emitted when a card is clicked.
    """

    image_selected = pyqtSignal(str)

    _CARD_SPACING = 10

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards: list[ImageCard] = []
        self._selected_path: str | None = None

        self._container = QWidget()
        self._container.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(self._CARD_SPACING)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.setWidget(self._container)

    def add_image(
        self,
        path: str,
        qimage: QImage,
        file_size: int,
        img_width: int,
        img_height: int,
    ) -> None:
        pixmap = QPixmap.fromImage(qimage)
        card = ImageCard(path, pixmap, file_size, img_width, img_height, self._container)
        card.clicked.connect(self._on_card_clicked)

        idx = len(self._cards)
        cols = self._column_count()
        self._grid.addWidget(card, idx // cols, idx % cols)
        self._cards.append(card)

    def clear(self) -> None:
        for card in self._cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_path = None

    def show_empty_message(self, text: str) -> None:
        self.clear()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        self._grid.addWidget(label, 0, 0)

    def card_count(self) -> int:
        return len(self._cards)

    def _column_count(self) -> int:
        available = self.viewport().width() - 24
        cols = max(1, available // (CARD_WIDTH + self._CARD_SPACING))
        return cols

    def _reflow(self) -> None:
        cols = self._column_count()
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // cols, i % cols)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._cards:
            self._reflow()

    def _on_card_clicked(self, path: str) -> None:
        if self._selected_path:
            for card in self._cards:
                if card.path == self._selected_path:
                    card.set_selected(False)
                    break

        self._selected_path = path
        for card in self._cards:
            if card.path == path:
                card.set_selected(True)
                break

        self.image_selected.emit(path)
