"""Widgets for the dimensions and units sections of the viewer metadata widget"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from napari.layers import Layer
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
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

    dim_diff = viewer_ndim - layer.ndim
    return [''] * dim_diff + list(layer.axis_labels)


def solve_setting_labels(
    viewer_labels: Sequence[str], layer_labels: Sequence[str]
) -> list[str]:
    """Compute the labels that would be written to the viewer."""
    viewer_ndim = len(viewer_labels)
    return [
        layer_label if layer_label else str(i - viewer_ndim)
        for i, layer_label in enumerate(layer_labels)
    ]


class AxisLabelTableModel(QAbstractTableModel):
    """Table model exposing viewer, layer, and derived setting labels."""

    VIEWER_COLUMN = 0
    SETTING_COLUMN = 1
    LAYER_COLUMN = 2
    _header_labels = ['Viewer', 'Setting', 'Layer']

    def __init__(
        self, napari_viewer: ViewerModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._napari_viewer = napari_viewer
        self._is_setting_data = False
        self._rows: list[AxisLabelRow] = []
        self.refresh()

    @property
    def rows(self) -> list[AxisLabelRow]:
        return list(self._rows)

    @property
    def header_labels(self) -> list[str]:
        return list(self._header_labels)

    @property
    def is_setting_data(self) -> bool:
        return self._is_setting_data

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
        if index.column() == self.VIEWER_COLUMN:
            return row.viewer_label
        if index.column() == self.SETTING_COLUMN:
            return row.setting_label
        if index.column() == self.LAYER_COLUMN:
            return row.layer_label
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = super().flags(index)
        if self._is_editable_column(index.column()):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(
        self,
        index: QModelIndex,
        value,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        if role != Qt.ItemDataRole.EditRole:
            return False

        new_value = str(value)

        if index.column() == self.VIEWER_COLUMN:
            viewer_labels = list(self._napari_viewer.dims.axis_labels)
            viewer_labels[index.row()] = new_value
            # This flag is needed to stop the conflict between the refresh and the viewer updating.
            self._is_setting_data = True
            try:
                self._napari_viewer.dims.axis_labels = tuple(viewer_labels)
            finally:
                self._is_setting_data = False

            row = self._rows[index.row()]
            layer_label = row.layer_label
            setting_label = (
                layer_label
                if layer_label
                else str(index.row() - len(self._rows))
            )
            self._rows[index.row()] = AxisLabelRow(
                axis_index=row.axis_index,
                viewer_label=new_value,
                setting_label=setting_label,
                layer_label=layer_label,
            )
            self.dataChanged.emit(
                self.index(index.row(), self.VIEWER_COLUMN),
                self.index(index.row(), self.SETTING_COLUMN),
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole],
            )
            return True

        if index.column() == self.LAYER_COLUMN:
            layer = self._napari_viewer.layers.selection.active
            if layer is None:
                return False

            layer_axis_index = self._layer_axis_index_for_row(index.row())
            if layer_axis_index is None:
                return False

            layer_labels = list(layer.axis_labels)
            layer_labels[layer_axis_index] = new_value
            self._is_setting_data = True
            try:
                layer.axis_labels = tuple(layer_labels)
            finally:
                self._is_setting_data = False

            row = self._rows[index.row()]
            setting_label = new_value if new_value else str(row.axis_index)
            self._rows[index.row()] = AxisLabelRow(
                axis_index=row.axis_index,
                viewer_label=row.viewer_label,
                setting_label=setting_label,
                layer_label=new_value,
            )
            self.dataChanged.emit(
                self.index(index.row(), self.SETTING_COLUMN),
                self.index(index.row(), self.LAYER_COLUMN),
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole],
            )
            return True

        return False

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

    def _is_editable_column(self, column: int) -> bool:
        return column in (self.VIEWER_COLUMN, self.LAYER_COLUMN)

    def _layer_axis_index_for_row(self, row_index: int) -> int | None:
        layer = self._napari_viewer.layers.selection.active
        if layer is None:
            return None

        viewer_ndim = self._napari_viewer.dims.ndim
        layer_axis_index = row_index - (viewer_ndim - layer.ndim)
        if layer_axis_index < 0:
            return None
        return layer_axis_index

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
                setting_label=setting_labels[i],
                layer_label=layer_labels[i],
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
        self._event_connected_layer: Layer | None = None

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)

        self._title_label: QLabel = QLabel('Dims labels')
        set_title_label_style(self._title_label)
        self._layout.addWidget(self._title_label)

        self._apply_layer_dim_labels_to_viewer_button: QPushButton = (
            QPushButton('Apply labels to viewer', parent=self)
        )
        self._apply_layer_dim_labels_to_viewer_button.clicked.connect(
            self._apply_layer_labels_to_viewer
        )
        self._layout.addWidget(self._apply_layer_dim_labels_to_viewer_button)

        self._table_model = AxisLabelTableModel(self._napari_viewer, self)
        self._label_table = LabelTable(self._table_model, self)
        self._layout.addWidget(self._label_table)
        self._layout.addStretch()

        self._napari_viewer.layers.selection.events.active.connect(
            self._on_layer_selection_changed
        )
        self._napari_viewer.dims.events.axis_labels.connect(
            self._on_viewer_axis_labels_changed
        )
        self._napari_viewer.dims.events.ndim.connect(
            self._on_viewer_ndim_changed
        )
        self._on_layer_selection_changed()

    def _apply_layer_labels_to_viewer(self) -> None:
        if self._napari_viewer.layers.selection.active is None:
            return
        self._refresh_table_model()
        self._napari_viewer.dims.axis_labels = tuple(
            row.setting_label for row in self._table_model.rows
        )

    def _on_layer_selection_changed(self) -> None:
        current_layer = self._napari_viewer.layers.selection.active
        if current_layer is self._event_connected_layer:
            self._refresh_table_model()
            return

        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.axis_labels.disconnect(
                    self._on_layer_axis_labels_changed
                )

        self._event_connected_layer = current_layer

        if current_layer is not None:
            current_layer.events.axis_labels.connect(
                self._on_layer_axis_labels_changed
            )

        self._refresh_table_model()

    def _on_layer_axis_labels_changed(self) -> None:
        if self._table_model.is_setting_data:
            return
        self._refresh_table_model()

    def _on_viewer_axis_labels_changed(self) -> None:
        if self._table_model.is_setting_data:
            return
        self._refresh_table_model()

    def _on_viewer_ndim_changed(self) -> None:
        self._refresh_table_model()

    def _refresh_table_model(self) -> None:
        self._table_model.refresh()

    def closeEvent(self, event) -> None:  # type: ignore
        with suppress(TypeError, ValueError, RuntimeError):
            self._napari_viewer.layers.selection.events.active.disconnect(
                self._on_layer_selection_changed
            )
        with suppress(TypeError, ValueError, RuntimeError):
            self._napari_viewer.dims.events.axis_labels.disconnect(
                self._on_viewer_axis_labels_changed
            )
        with suppress(TypeError, ValueError, RuntimeError):
            self._napari_viewer.dims.events.ndim.disconnect(
                self._on_viewer_ndim_changed
            )

        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.axis_labels.disconnect(
                    self._on_layer_axis_labels_changed
                )

        super().closeEvent(event)


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
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self.setCornerButtonEnabled(False)
        self.setSortingEnabled(False)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
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
        self.resizeRowsToContents()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
