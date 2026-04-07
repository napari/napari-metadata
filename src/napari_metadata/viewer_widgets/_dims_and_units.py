"""Widgets for the dimensions and units sections of the viewer metadata widget"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from napari.layers import Layer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
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
        napari_viewer: ViewerModel,
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
        self._labels_layout: QHBoxLayout = QHBoxLayout(self._labels_container)
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
        clear_layout(self._labels_layout)

        ndim = self._napari_viewer.dims.ndim
        layer = self._napari_viewer.layers.selection.active

        index_list = [str(a - ndim) for a in range(ndim)]
        index_container = LabelContainer('Index', index_list, self)

        viewer_container = LabelContainer(
            'Viewer', self._napari_viewer.dims.axis_labels
        )

        layer_labels = self._solve_layer_to_viewer_list(ndim, layer)
        layer_container = LabelContainer('Layer', layer_labels)

        setting_list = self._solve_setting_labels_list(
            self._napari_viewer.dims.axis_labels, layer_labels
        )
        setting_container = LabelContainer('Set', setting_list)

        self._labels_layout.addWidget(index_container)
        self._labels_layout.addWidget(viewer_container)
        self._labels_layout.addWidget(layer_container)
        self._labels_layout.addWidget(setting_container)

    def _apply_layer_labels_to_viewer(self) -> None:
        if self._napari_viewer.layers.selection.active is None:
            return
        layer_labels = self._solve_layer_to_viewer_list(
            self._napari_viewer.dims.ndim,
            self._napari_viewer.layers.selection.active,
        )
        self._napari_viewer.dims.axis_labels = tuple(
            self._solve_setting_labels_list(
                self._napari_viewer.dims.axis_labels, layer_labels
            )
        )

    def _solve_layer_to_viewer_list(
        self, ndim: int, layer: Layer | None
    ) -> list[str]:
        if layer is None:
            return [''] * ndim
        return_list: list[str] = []
        dim_diff = ndim - layer.ndim
        for i in range(ndim):
            if i < dim_diff:
                return_list.append('')
            else:
                return_list.append(layer.axis_labels[i - dim_diff])
        return return_list

    def _solve_setting_labels_list(
        self, viewer_labels: Sequence[str], layer_labels: Sequence[str]
    ) -> list[str]:
        return_list: list[str] = []
        for a in range(len(viewer_labels)):
            if layer_labels[a] == '':
                return_list.append(str(a - len(viewer_labels)))
            else:
                return_list.append(layer_labels[a])
        return return_list


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


class LabelContainer(QWidget):
    def __init__(
        self, title: str, labels: Sequence[str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent=parent)

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self._title_label = QLabel(title, parent=self)
        set_title_label_style(self._title_label)
        self._layout.addWidget(self._title_label)

        for label_text in labels:
            label = QLabel(label_text, self)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(label)
