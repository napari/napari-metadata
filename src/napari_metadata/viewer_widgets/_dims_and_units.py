"""Widgets for the dimensions and units sections of the viewer metadata widget"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel


class DimsAndUnitsWidget(QWidget):
    """Dimensions and units section of the viewer metadata widget"""

    def __init__(
        self,
        napari_viewer,
        *,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        self._napari_viewer = napari_viewer

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)

        self._axis_display_widget = AxisLabelsDisplayWidget(
            self._napari_viewer
        )

        self._layout.addWidget(self._axis_display_widget)

        self._layout.addStretch()


class AxisLabelsDisplayWidget(QWidget):
    def __init__(
        self, napari_viewer: ViewerModel, *, parent: QWidget | None = None
    ):
        super().__init__(parent=parent)

        self._napairi_viewer = napari_viewer

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)

        self._title_label: QLabel = QLabel('Dims labels')
        set_title_label_style(self._title_label)
        self._layout.addWidget(self._title_label)

        return


def set_title_label_style(label: QLabel) -> QLabel:
    label.setStyleSheet('font-weight: bold;font-size: 15pt')
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
