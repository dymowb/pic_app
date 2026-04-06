"""
Settings dialog — similarity threshold and scoring weights.
Values are read from / written to a JSON config file.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config import DEFAULTS, load_settings, save_settings  # noqa: F401


class _LabelledSlider(QWidget):
    """A slider with a live value label displayed beside it."""

    def __init__(
        self,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suffix = suffix

        from PyQt6.QtWidgets import QHBoxLayout

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setValue(value)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval((maximum - minimum) // 5 or 1)

        self._value_label = QLabel(f"{value}{suffix}")
        self._value_label.setFixedWidth(48)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._slider.valueChanged.connect(
            lambda v: self._value_label.setText(f"{v}{self._suffix}")
        )

        layout.addWidget(self._slider)
        layout.addWidget(self._value_label)

    @property
    def value(self) -> int:
        return self._slider.value()

    def connect_changed(self, slot) -> None:
        self._slider.valueChanged.connect(slot)


class SettingsDialog(QDialog):
    """Modal settings dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        self._settings = load_settings()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        sim_group = QGroupBox("Similarity Detection")
        sim_form = QFormLayout(sim_group)

        self._threshold_slider = _LabelledSlider(
            minimum=0,
            maximum=20,
            value=self._settings["similarity_threshold"],
        )
        sim_form.addRow("Threshold (0 = exact, 20 = relaxed):", self._threshold_slider)

        hint = QLabel(
            "Lower values find only near-identical images.\n"
            "Higher values also group images that look similar but differ more."
        )
        hint.setStyleSheet("color: #666; font-size: 11px;")
        hint.setWordWrap(True)
        sim_form.addRow("", hint)
        layout.addWidget(sim_group)

        weights_group = QGroupBox("Scoring Weights (must total 100%)")
        weights_form = QFormLayout(weights_group)

        w = self._settings["weights"]
        self._w_sharpness = _LabelledSlider(0, 100, w["sharpness"], suffix="%")
        self._w_exposure = _LabelledSlider(0, 100, w["exposure"], suffix="%")
        self._w_resolution = _LabelledSlider(0, 100, w["resolution"], suffix="%")

        self._total_label = QLabel()
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._update_total_label()

        for slider in (self._w_sharpness, self._w_exposure, self._w_resolution):
            slider.connect_changed(lambda _: self._update_total_label())

        weights_form.addRow("Sharpness:", self._w_sharpness)
        weights_form.addRow("Exposure:", self._w_exposure)
        weights_form.addRow("Resolution:", self._w_resolution)
        weights_form.addRow("Total:", self._total_label)
        layout.addWidget(weights_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_total_label(self) -> None:
        total = self._w_sharpness.value + self._w_exposure.value + self._w_resolution.value
        color = "#090" if total == 100 else "#c00"
        self._total_label.setText(f"<span style='color:{color};font-weight:bold'>{total}%</span>")

    def _on_accept(self) -> None:
        total = self._w_sharpness.value + self._w_exposure.value + self._w_resolution.value
        if total != 100:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Weights",
                f"Scoring weights must total 100%. Current total: {total}%.",
            )
            return

        self._settings["similarity_threshold"] = self._threshold_slider.value
        self._settings["weights"] = {
            "sharpness": self._w_sharpness.value,
            "exposure": self._w_exposure.value,
            "resolution": self._w_resolution.value,
        }
        save_settings(self._settings)
        self.accept()
