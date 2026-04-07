"""Widgets for the dimensions and units sections of the viewer metadata widget"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QGridLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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

        self._napari_viewer = napari_viewer

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)

        self._title_label: QLabel = QLabel('Dims labels')
        set_title_label_style(self._title_label)
        self._layout.addWidget(self._title_label)

        self._labels_container: QWidget = QWidget(parent=self)
        self._labels_layout: QGridLayout = QGridLayout(self._labels_container)
        self._labels_container.setLayout(self._labels_layout)
        self._layout.addWidget(self._labels_container)

        self._populate_labels_grid()

        self._update_button: QPushButton = QPushButton(
            'Update labels', parent=self
        )
        self._update_button.clicked.connect(self._populate_labels_grid)
        self._layout.addWidget(self._update_button)

        self._apply_layer_dim_labels_to_viewer_button: QPushButton = (
            QPushButton('Apply labels to viewer', parent=self)
        )
        self._apply_layer_dim_labels_to_viewer_button.clicked.connect(
            self._apply_layer_labels_to_viewer
        )
        self._layout.addWidget(self._apply_layer_dim_labels_to_viewer_button)

        return

    def _populate_labels_grid(self) -> None:
        number_of_dims = self._napari_viewer.dims.ndim
        layer = self._napari_viewer.layers.selection.active
        layer_dims = 0
        if layer is not None:
            layer_dims = layer.ndim
        dims_difference = number_of_dims - layer_dims
        clear_layout(self._labels_layout)
        index_label: QLabel = QLabel('Index', parent=self._labels_container)
        index_label.setStyleSheet('font-weight: bold; font-size: 10pt')
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewer_label: QLabel = QLabel('Viewer', parent=self._labels_container)
        viewer_label.setStyleSheet('font-weight: bold; font-size: 10pt')
        viewer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_label: QLabel = QLabel('Layer', parent=self._labels_container)
        layer_label.setStyleSheet('font-weight: bold; font-size: 10pt')
        layer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._labels_layout.addWidget(index_label, 0, 0)
        self._labels_layout.addWidget(viewer_label, 0, 1)
        self._labels_layout.addWidget(layer_label, 0, 2)
        for i in range(number_of_dims):
            current_index_label = QLabel(
                str(i - number_of_dims), parent=self._labels_container
            )
            current_index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            current_viewer_label = QLabel(
                self._napari_viewer.dims.axis_labels[i],
                parent=self._labels_container,
            )
            current_viewer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            current_layer_text: str = ''
            if i < dims_difference:
                current_layer_text = str(i - number_of_dims)
            else:
                if layer is not None:
                    current_layer_text = layer.axis_labels[i - dims_difference]
            current_layer_label = QLabel(
                current_layer_text, parent=self._labels_container
            )
            current_layer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._labels_layout.addWidget(current_index_label, i + 1, 0)
            self._labels_layout.addWidget(current_viewer_label, i + 1, 1)
            self._labels_layout.addWidget(current_layer_label, i + 1, 2)

    def _apply_layer_labels_to_viewer(self) -> None:
        self._napari_viewer.dims.axis_labels = (
            self._napari_viewer.layers.selection.active.axis_labels
        )


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is not None and item.widget() is not None:
            widget = item.widget()
            widget.deleteLater()  # type: ignore


def set_title_label_style(label: QLabel) -> QLabel:
    label.setStyleSheet('font-weight: bold;font-size: 15pt')
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
