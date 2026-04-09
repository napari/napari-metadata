"""Widgets for the dimensions and units sections of the viewer metadata widget"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from napari.layers import Layer
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel


@dataclass(frozen=True)
class AxisLabelRow:
    axis_index: int
    viewer_label: str
    layer_label: str
    setting_label: str


def solve_layer_to_viewer_labels(
    viewer_ndim: int, layer: Layer | None
) -> list[str]:
    """Map active-layer axis labels into viewer dimensionality."""
    if layer is None:
        return [''] * viewer_ndim

    return_list: list[str] = []
    dim_diff = viewer_ndim - layer.ndim
    for i in range(viewer_ndim):
        if i < dim_diff:
            return_list.append('')
        else:
            return_list.append(layer.axis_labels[i - dim_diff])
    return return_list


def solve_setting_labels(
    viewer_labels: Sequence[str], layer_labels: Sequence[str]
) -> list[str]:
    """Compute the labels that would be written to the viewer."""
    return_list: list[str] = []
    for i in range(len(viewer_labels)):
        if layer_labels[i] == '':
            return_list.append(str(i - len(viewer_labels)))
        else:
            return_list.append(layer_labels[i])
    return return_list


class AxisLabelTableModel(QAbstractTableModel):
    """Table model exposing viewer, layer, and derived setting labels."""

    _header_labels = ['Viewer', 'Layer', 'Setting']

    def __init__(
        self, napari_viewer: ViewerModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._napari_viewer = napari_viewer
        self._rows: list[AxisLabelRow] = []
        self.refresh()

    @property
    def rows(self) -> list[AxisLabelRow]:
        return list(self._rows)

    @property
    def header_labels(self) -> list[str]:
        return list(self._header_labels)

    def refresh(self) -> None:
        self.beginResetModel()
        self._rows = self._build_rows()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._header_labels)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | int | None:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        if role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None

        row = self._rows[index.row()]
        if index.column() == 0:
            return row.viewer_label
        if index.column() == 1:
            return row.layer_label
        if index.column() == 2:
            return row.setting_label
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._header_labels):
                return self._header_labels[section]
            return None

        if orientation == Qt.Orientation.Vertical:
            if 0 <= section < len(self._rows):
                return str(self._rows[section].axis_index)
            return None

        return None

    def _build_rows(self) -> list[AxisLabelRow]:
        viewer_ndim = self._napari_viewer.dims.ndim
        viewer_labels = self._napari_viewer.dims.axis_labels
        layer = self._napari_viewer.layers.selection.active
        layer_labels = solve_layer_to_viewer_labels(viewer_ndim, layer)
        setting_labels = solve_setting_labels(viewer_labels, layer_labels)

        return [
            AxisLabelRow(
                axis_index=i - viewer_ndim,
                viewer_label=viewer_labels[i],
                layer_label=layer_labels[i],
                setting_label=setting_labels[i],
            )
            for i in range(viewer_ndim)
        ]


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

        self._table_model = AxisLabelTableModel(self._napari_viewer, self)
        self._label_table = LabelTable(self._table_model, self)
        self._labels_layout.addWidget(self._label_table)

        self._update_button: QPushButton = QPushButton(
            'Update labels', parent=self
        )
        self._update_button.clicked.connect(self._table_model.refresh)
        self._layout.addWidget(self._update_button)

        self._apply_layer_dim_labels_to_viewer_button: QPushButton = (
            QPushButton('Apply labels to viewer', parent=self)
        )
        self._apply_layer_dim_labels_to_viewer_button.clicked.connect(
            self._apply_layer_labels_to_viewer
        )
        self._layout.addWidget(self._apply_layer_dim_labels_to_viewer_button)

    def _apply_layer_labels_to_viewer(self) -> None:
        if self._napari_viewer.layers.selection.active is None:
            return
        self._table_model.refresh()
        self._napari_viewer.dims.axis_labels = tuple(
            row.setting_label for row in self._table_model.rows
        )


def set_title_label_style(label: QLabel) -> QLabel:
    label.setStyleSheet('font-weight: bold;font-size: 15pt')
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class LabelTable(QTableView):
    """View for viewer, layer, and derived setting axis labels."""

    def __init__(
        self,
        model: AxisLabelTableModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self._table_model = model

        self._build_table()

    def _build_table(self) -> None:
        """Configure the table view."""
        self.setModel(self._table_model)
        self.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        horizontal_header = self.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )

        vertical_header = self.verticalHeader()
        if vertical_header is not None:
            vertical_header.setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
