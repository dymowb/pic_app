"""
GroupPanel — horizontal strip for one duplicate group.

After Phase 5:
  - Recommended card gets a green "Best – Keep" badge
  - Runner-up card gets a blue "Runner-up" badge (groups ≥ 3)
  - Header shows: ⭐ Keep: filename — reason
  - Clicking any other card moves the "Best – Keep" badge (manual override)
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

    Signals
    -------
    image_selected(path)      — bubbled up from any card click (for preview)
    keep_changed(group_index, path)
                               — emitted when the user changes their keep pick
    """

    image_selected = pyqtSignal(str)
    keep_changed   = pyqtSignal(int, str)   # (group_index, path)

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
        self._recommended_path: str | None = None
        self._keep_path: str | None = None
        self._runner_up_path: str | None = None
        self._group_index = group_index
        self._image_data = image_data

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(4)

        self._header_widget = self._make_header()
        outer.addWidget(self._header_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFixedHeight(CARD_HEIGHT + 12)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_widget = QWidget()
        self._cards_layout = QHBoxLayout(cards_widget)
        self._cards_layout.setContentsMargins(4, 4, 4, 4)
        self._cards_layout.setSpacing(8)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for path_str, pixmap, file_size, img_w, img_h in self._image_data:
            card = ImageCard(path_str, pixmap, file_size, img_w, img_h, cards_widget)
            card.clicked.connect(self._on_card_clicked)
            self._cards_layout.addWidget(card)
            self._cards[path_str] = card

        self._cards_layout.addStretch()
        scroll.setWidget(cards_widget)
        outer.addWidget(scroll)

    def _make_header(
        self,
        rec_name: str = "",
        reason: str = "",
        total_bytes: int | None = None,
    ) -> QWidget:
        header = QWidget()
        header.setStyleSheet("background: #e8eaf6; border-radius: 4px;")
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

        if rec_name and reason:
            sep = QLabel("  |")
            sep.setStyleSheet("color: #aaa;")
            layout.addWidget(sep)

            rec_label = QLabel(f"⭐  Keep: <b>{rec_name}</b> — {reason}")
            rec_label.setStyleSheet("color: #1a5c1a; font-size: 10px;")
            layout.addWidget(rec_label)

        layout.addStretch()

        if total_bytes is None:
            total_bytes = sum(sz for _, _, sz, _, _ in self._image_data)
        size_label = QLabel(_human_size(total_bytes))
        size_label.setStyleSheet("color: #555; font-size: 9px;")
        layout.addWidget(size_label)

        return header

    def apply_scores(self, scores: list) -> None:
        from ui.image_card import ImageCard

        if not scores:
            return

        best = scores[0]
        self._recommended_path = str(best.path)
        self._keep_path = self._recommended_path

        runner_up_path = str(scores[1].path) if len(scores) >= 3 else None
        self._runner_up_path = runner_up_path

        for s in scores:
            path_str = str(s.path)
            if path_str not in self._cards:
                continue
            card = self._cards[path_str]

            if s.rank == 1:
                card.set_badge(ImageCard.BADGE_BEST)
            elif s.rank == 2 and runner_up_path:
                card.set_badge(ImageCard.BADGE_RUNNER_UP)
            else:
                card.set_badge(ImageCard.BADGE_NONE)

            existing = card.toolTip() or ""
            score_line = f"<hr><b>Quality score: {s.score:.0f} / 100</b>"
            if s.rank == 1 and best.reason:
                score_line += f"<br><i>{best.reason}</i>"
            card.setToolTip(existing + score_line if existing else score_line)

        rec_name = Path(self._recommended_path).name
        self._replace_header(rec_name, best.reason)

    def get_keep_path(self) -> str | None:
        return self._keep_path

    def card_paths(self) -> list[str]:
        return list(self._cards.keys())

    def _replace_header(self, rec_name: str, reason: str) -> None:
        total_bytes = sum(sz for _, _, sz, _, _ in self._image_data)
        new_header = self._make_header(rec_name, reason, total_bytes)
        layout = self.layout()
        old = layout.takeAt(0).widget()
        if old:
            old.deleteLater()
        layout.insertWidget(0, new_header)
        self._header_widget = new_header

    def _on_card_clicked(self, path: str) -> None:
        if self._selected_path and self._selected_path in self._cards:
            self._cards[self._selected_path].set_selected(False)
        self._selected_path = path
        self._cards[path].set_selected(True)
        self.image_selected.emit(path)

        if self._keep_path and path != self._keep_path:
            from ui.image_card import ImageCard as IC
            if self._keep_path in self._cards:
                self._cards[self._keep_path].set_badge(IC.BADGE_NONE)
            if self._runner_up_path and self._runner_up_path in self._cards:
                self._cards[self._runner_up_path].set_badge(IC.BADGE_NONE)

            self._keep_path = path
            self._cards[path].set_badge(IC.BADGE_BEST)
            self._replace_header(Path(path).name, "Manual pick")
            self.keep_changed.emit(self._group_index, path)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.0f} TB"
