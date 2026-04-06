"""
ImageCard — a single clickable thumbnail card shown in the grid.

Displays:
  - Thumbnail image (centred, max 160×160)
  - Filename (truncated with ellipsis)
  - File size in human-readable form
  - Optional badge (e.g. "Best – Keep", "Runner-up") set in Phase 5
  - Rich HTML tooltip showing quality metrics (set after Phase 4 analysis)
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

CARD_WIDTH = 180
THUMB_SIZE = 160
CARD_HEIGHT = THUMB_SIZE + 52  # thumb + filename + size labels


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.0f} TB"


class ImageCard(QWidget):
    """
    A clickable thumbnail card.

    Signals
    -------
    clicked(path)  — emitted when the card is left-clicked.
    """

    clicked = pyqtSignal(str)

    # Badge styles (populated in Phase 5)
    BADGE_NONE = 0
    BADGE_BEST = 1
    BADGE_RUNNER_UP = 2

    _BADGE_COLOR = {
        BADGE_BEST: ("#1a7a1a", "#e8f5e9", "Best – Keep"),
        BADGE_RUNNER_UP: ("#1a4a8a", "#e3f0ff", "Runner-up"),
    }

    def __init__(
        self,
        path: str,
        pixmap: QPixmap,
        file_size: int,
        img_width: int,
        img_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.path = path
        self.file_size = file_size
        self.img_width = img_width
        self.img_height = img_height
        self._selected = False
        self._badge = self.BADGE_NONE
        self._badge_text = ""

        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(pixmap, file_size)

    def _build_ui(self, pixmap: QPixmap, file_size: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(2)

        # Thumbnail
        self._thumb_label = QLabel()
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        scaled = pixmap.scaled(
            THUMB_SIZE,
            THUMB_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumb_label.setPixmap(scaled)
        layout.addWidget(self._thumb_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Filename
        name = Path(self.path).name
        filename_label = QLabel(name)
        filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filename_label.setMaximumWidth(CARD_WIDTH - 12)
        filename_label.setWordWrap(False)
        font = QFont()
        font.setPointSize(8)
        filename_label.setFont(font)
        filename_label.setToolTip(self.path)
        fm = filename_label.fontMetrics()
        elided = fm.elidedText(name, Qt.TextElideMode.ElideMiddle, CARD_WIDTH - 12)
        filename_label.setText(elided)
        layout.addWidget(filename_label)

        # File size + dimensions
        size_label = QLabel(f"{_human_size(file_size)}  {img_width}×{img_height}")
        size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_label.setStyleSheet("color: #777; font-size: 9px;")
        layout.addWidget(size_label)

    # ------------------------------------------------------------------
    # Selection & badge
    # ------------------------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def set_badge(self, badge: int) -> None:
        self._badge = badge
        self.update()

    def set_metrics(self, metrics) -> None:
        """
        Attach quality metrics (ImageMetrics) and update the tooltip.
        Called by the main window after AnalysisWorker emits metrics_ready.
        """
        self.setToolTip(_metrics_tooltip(metrics))

    # ------------------------------------------------------------------
    # Paint: border around card when selected / badged
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        if self._badge in self._BADGE_COLOR:
            border_hex, bg_hex, label = self._BADGE_COLOR[self._badge]
            painter.setPen(QColor(border_hex))
            painter.setBrush(QColor(bg_hex))
            painter.drawRoundedRect(rect, 6, 6)

            # Badge label strip at top
            badge_rect = rect.adjusted(0, 0, 0, -(rect.height() - 18))
            painter.fillRect(badge_rect, QColor(border_hex))
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPointSize(7)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label)
        elif self._selected:
            painter.setPen(QColor("#2979ff"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 6, 6)
        else:
            painter.setPen(QColor("#ddd"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 6, 6)

        painter.end()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Tooltip helper
# ---------------------------------------------------------------------------

def _bar(value: float, max_value: float = 100.0, width: int = 100) -> str:
    """Return an HTML progress-bar-like string for a metric value."""
    pct = min(100, int(value / max_value * 100)) if max_value > 0 else 0
    filled = int(width * pct / 100)
    color = "#4caf50" if pct >= 60 else ("#ff9800" if pct >= 30 else "#f44336")
    bar = f"<span style='background:{color};display:inline-block;width:{filled}px;height:8px;'></span>"
    empty = f"<span style='background:#ddd;display:inline-block;width:{width - filled}px;height:8px;'></span>"
    return bar + empty


def _metrics_tooltip(metrics) -> str:
    """Build a rich HTML tooltip from an ImageMetrics object."""
    sharp_display = min(100.0, metrics.sharpness / 10.0)
    mp = metrics.resolution / 1_000_000

    return (
        "<table style='font-size:11px; white-space:nowrap;'>"
        f"<tr><td><b>Resolution</b></td><td>&nbsp;{metrics.width}×{metrics.height}"
        f" ({mp:.1f} MP)</td></tr>"
        f"<tr><td><b>Sharpness</b></td><td>&nbsp;{metrics.sharpness:.0f} "
        f"&nbsp;{_bar(sharp_display)}</td></tr>"
        f"<tr><td><b>Exposure</b></td><td>&nbsp;{metrics.exposure:.0f}/100 "
        f"&nbsp;{_bar(metrics.exposure)}</td></tr>"
        f"<tr><td><b>Noise score</b></td><td>&nbsp;{metrics.noise:.0f}/100 "
        f"&nbsp;{_bar(metrics.noise)}</td></tr>"
        "</table>"
    )
