"""
PreviewPanel — right-side panel that shows a full-size image preview
along with its metadata (filename, dimensions, file size, full path).
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.0f} TB"


class PreviewPanel(QWidget):
    """
    Displays a full-resolution preview of a selected image.

    Call set_image(path) to load a new image.
    Call clear() to return to the placeholder state.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self._current_path: Path | None = None
        self._raw_pixmap: QPixmap | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Scrollable image area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background: #1e1e1e; border: none;")

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: transparent;")
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self._scroll.setWidget(self._image_label)
        layout.addWidget(self._scroll, stretch=1)

        # Metadata area
        meta_widget = QWidget()
        meta_layout = QVBoxLayout(meta_widget)
        meta_layout.setContentsMargins(4, 4, 4, 4)
        meta_layout.setSpacing(2)

        self._name_label = QLabel("No image selected")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(True)
        self._name_label.setStyleSheet("font-weight: bold; font-size: 11px;")

        self._dims_label = QLabel("")
        self._dims_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dims_label.setStyleSheet("color: #555; font-size: 10px;")

        self._path_label = QLabel("")
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._path_label.setWordWrap(True)
        self._path_label.setStyleSheet("color: #888; font-size: 9px;")
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        meta_layout.addWidget(self._name_label)
        meta_layout.addWidget(self._dims_label)
        meta_layout.addWidget(self._path_label)
        layout.addWidget(meta_widget)

        # Placeholder shown when no image is selected
        self._set_placeholder()

    def _set_placeholder(self) -> None:
        self._image_label.setText(
            "<span style='color:#666;font-size:13px;'>"
            "Select an image to preview it here."
            "</span>"
        )
        self._name_label.setText("No image selected")
        self._dims_label.setText("")
        self._path_label.setText("")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_image(self, path: str) -> None:
        """Load and display the image at path."""
        p = Path(path)
        try:
            pixmap = QPixmap(str(p))
            if pixmap.isNull():
                raise ValueError("QPixmap returned null")
        except Exception:
            self._image_label.setText(
                "<span style='color:#c00;'>Could not load image.</span>"
            )
            return

        self._raw_pixmap = pixmap
        self._current_path = p
        self._refresh_image()

        # Metadata
        self._name_label.setText(p.name)
        size_str = _human_size(p.stat().st_size) if p.exists() else "?"
        self._dims_label.setText(
            f"{pixmap.width()} × {pixmap.height()} px  ·  {size_str}"
        )
        self._path_label.setText(str(p))

    def clear(self) -> None:
        self._raw_pixmap = None
        self._current_path = None
        self._set_placeholder()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh_image(self) -> None:
        if self._raw_pixmap is None:
            return
        available = self._scroll.size() - self._scroll.contentsMargins().topLeft().toPointF()
        scaled = self._raw_pixmap.scaled(
            self._scroll.width() - 4,
            self._scroll.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh_image()
