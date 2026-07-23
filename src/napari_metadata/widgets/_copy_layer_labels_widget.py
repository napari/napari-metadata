from contextlib import suppress
from dataclasses import dataclass

from napari.components import Dims, LayerList
from napari.layers import Layer
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class CopyAxisLabelRow:
    axis_index: int
    layer_label: str
    setting_label: str
    affected_layers: str


class CopyAxisLabelTableModel(QAbstractTableModel):
    CURRENT_LAYER_COLUMN = 0
    SETTING_COLUMN = 1
    AFFECTED_LAYERS_COLUMN = 2
    _header_labels = ['Current layer', 'Setting', 'Affected layers']

    def __init__(
        self,
        layer_list: LayerList,
        viewer_dims: Dims,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._layer_list = layer_list
        self._viewer_dims = viewer_dims
        self._is_setting_data = False
        self._affected_layers: dict[int, list[str]] = {}
        self._rows: list[CopyAxisLabelRow] = []
        self.refresh()

    @property
    def affected_layers(self) -> dict[int, list[str]]:
        return {
            axis_index: list(layer_names)
            for axis_index, layer_names in self._affected_layers.items()
        }

    @property
    def is_setting_data(self) -> bool:
        return self._is_setting_data

    def refresh(self) -> None:
        self.beginResetModel()
        self._rows = self._build_rows()
        self._calculate_affected_layers()
        self.endResetModel()

    def _calculate_affected_layers(self) -> None:
        """Recalculate layers affected by the current setting labels."""
        self._affected_layers.clear()
        viewer_ndim = self._viewer_dims.ndim
        setting_labels = [row.setting_label for row in self._rows]

        for row_index, setting_label in enumerate(setting_labels):
            affected_layers: list[str] = []
            for layer in self._layer_list:
                layer_axis_index = row_index - (viewer_ndim - layer.ndim)
                if not 0 <= layer_axis_index < layer.ndim:
                    continue
                if layer.axis_labels[layer_axis_index] != setting_label:
                    affected_layers.append(layer.name)
            self._affected_layers[row_index] = affected_layers

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._header_labels)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | int | None:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        row = self._rows[index.row()]
        if index.column() == self.CURRENT_LAYER_COLUMN:
            return row.layer_label
        if index.column() == self.SETTING_COLUMN:
            return row.setting_label
        if index.column() == self.AFFECTED_LAYERS_COLUMN:
            return row.affected_layers
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = super().flags(index)
        if index.column() == self.AFFECTED_LAYERS_COLUMN:
            return flags & ~Qt.ItemFlag.ItemIsEditable
        if (
            index.column() == self.CURRENT_LAYER_COLUMN
            and self._layer_axis_index_for_row(index.row()) is None
        ):
            return flags & ~Qt.ItemFlag.ItemIsEditable
        return flags | Qt.ItemFlag.ItemIsEditable

    def setData(
        self,
        index: QModelIndex,
        value,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        new_value = str(value)

        if index.column() == self.CURRENT_LAYER_COLUMN:
            layer = self._layer_list.selection.active
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

            self.refresh()
            return True

        if index.column() == self.SETTING_COLUMN:
            row = self._rows[index.row()]
            self._rows[index.row()] = CopyAxisLabelRow(
                axis_index=row.axis_index,
                layer_label=row.layer_label,
                setting_label=new_value,
                affected_layers=row.affected_layers,
            )
            self._calculate_affected_layers()
            self.dataChanged.emit(
                index,
                index,
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
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(
            self._header_labels
        ):
            return self._header_labels[section]
        if orientation == Qt.Orientation.Vertical and 0 <= section < len(
            self._rows
        ):
            return str(self._rows[section].axis_index)
        return None

    def _build_rows(self) -> list[CopyAxisLabelRow]:
        viewer_ndim = self._viewer_dims.ndim
        layer = self._layer_list.selection.active

        if layer is None:
            layer_labels = [''] * viewer_ndim
        else:
            layer_labels = [''] * (viewer_ndim - layer.ndim) + list(
                layer.axis_labels
            )

        return [
            CopyAxisLabelRow(
                axis_index=i - viewer_ndim,
                layer_label=layer_labels[i],
                setting_label=(
                    layer_labels[i]
                    if layer_labels[i]
                    else str(i - viewer_ndim)
                ),
                affected_layers='',
            )
            for i in range(viewer_ndim)
        ]

    def _layer_axis_index_for_row(self, row_index: int) -> int | None:
        layer = self._layer_list.selection.active
        if layer is None:
            return None

        layer_axis_index = row_index - (self._viewer_dims.ndim - layer.ndim)
        if not 0 <= layer_axis_index < layer.ndim:
            return None
        return layer_axis_index


class CopyAxisLabelTable(QTableView):
    def __init__(
        self,
        model: CopyAxisLabelTableModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self.setModel(model)
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
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._model.modelReset.connect(self._on_model_reset)
        self._populate_affected_widgets()

    def _create_affected_widget(self, affected_layers: list[str]) -> QWidget:
        if not affected_layers:
            return QLabel('None', parent=self)

        combo = QComboBox(parent=self)
        combo.addItem('Show affected')
        combo.addItems(affected_layers)
        combo.setCurrentIndex(0)
        combo.activated.connect(lambda _: combo.setCurrentIndex(0))
        return combo

    def _populate_affected_widgets(self) -> None:
        for row_index in range(self._model.rowCount()):
            index = self._model.index(
                row_index,
                CopyAxisLabelTableModel.AFFECTED_LAYERS_COLUMN,
            )
            affected_layers = self._model.affected_layers.get(row_index, [])
            self.setIndexWidget(
                index,
                self._create_affected_widget(affected_layers),
            )

    def _content_height(self) -> int:
        self.resizeRowsToContents()
        height = 2 * self.frameWidth()
        horizontal_header = self.horizontalHeader()
        if horizontal_header is not None and not horizontal_header.isHidden():
            height += horizontal_header.height()
        vertical_header = self.verticalHeader()
        if vertical_header is not None:
            height += vertical_header.length()
        height += 2
        return height

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(self._content_height())
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setHeight(self._content_height())
        return hint

    def _on_model_reset(self) -> None:
        self.resizeRowsToContents()
        self._populate_affected_widgets()
        self.updateGeometry()


class CopyLayerLabelsToAllWidget(QWidget):
    def __init__(
        self, layer_list: LayerList, viewer_dims: Dims, parent_widget: QWidget
    ) -> None:
        super().__init__(parent_widget)
        self.ll = layer_list
        self._viewer_dims = viewer_dims
        self._parent_widget = parent_widget
        self._event_connected_layer: Layer | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._copy_labels_title = QLabel('Copy layer labels to all layers')
        self._copy_labels_title.setStyleSheet('font-weight: bold')
        self._layout.addWidget(self._copy_labels_title)

        self._template_c = QWidget()
        self._template_c_layout = QHBoxLayout()
        self._template_c_layout.setContentsMargins(0, 0, 0, 0)
        self._template_c.setLayout(self._template_c_layout)
        self._layout.addWidget(self._template_c)

        self._template_layer_l = QLabel('Template layer name:')
        self._template_layer_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._template_layer_l.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_c_layout.addWidget(self._template_layer_l)

        self._layer_l = QLabel('')
        self._layer_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._layer_l.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_c_layout.addWidget(self._layer_l)

        self._template_c_layout.addStretch()

        self._all_layers_title_c = QWidget()
        self._all_layers_title_c_layout = QHBoxLayout()
        self._all_layers_title_c_layout.setContentsMargins(0, 0, 0, 0)
        self._all_layers_title_c.setLayout(self._all_layers_title_c_layout)
        self._layout.addWidget(self._all_layers_title_c)

        self._resulting_labels_title = QLabel('Resulting labels')
        self._resulting_labels_title.setStyleSheet('font-weight: bold')
        self._resulting_labels_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._resulting_labels_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._all_layers_title_c_layout.addWidget(self._resulting_labels_title)

        self._affected_layers_number_l = QLabel('Affected layers:')
        self._affected_layers_number_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._all_layers_title_c_layout.addWidget(
            self._affected_layers_number_l
        )

        self._table_model = CopyAxisLabelTableModel(self.ll, viewer_dims, self)
        self._label_table = CopyAxisLabelTable(self._table_model, self)
        self._layout.addWidget(self._label_table)
        self._table_model.modelReset.connect(
            self._update_affected_layers_count
        )
        self._table_model.dataChanged.connect(
            self._update_affected_layers_count
        )
        self._update_affected_layers_count()

        self.ll.selection.events.active.connect(
            self._on_layer_selection_changed
        )
        self._viewer_dims.events.ndim.connect(self._on_viewer_ndim_changed)
        self._on_layer_selection_changed()

    def _on_layer_selection_changed(self) -> None:
        """Update displays and layer-event connections after selection changes."""
        current_layer = self.ll.selection.active

        if current_layer is self._event_connected_layer:
            self._refresh_display()
            return

        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.name.disconnect(
                    self._on_layer_name_changed
                )
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.axis_labels.disconnect(
                    self._on_layer_axis_labels_changed
                )

        self._event_connected_layer = current_layer

        if current_layer is not None:
            current_layer.events.name.connect(self._on_layer_name_changed)
            current_layer.events.axis_labels.connect(
                self._on_layer_axis_labels_changed
            )

        self._refresh_display()

    def _refresh_display(self) -> None:
        active_layer = self.ll.selection.active
        self._layer_l.setText(active_layer.name if active_layer else '')
        self._table_model.refresh()

    def _update_affected_layers_count(self) -> None:
        """Update the count of unique layers affected across all dimensions."""
        affected_layers = {
            layer_name
            for layer_names in self._table_model.affected_layers.values()
            for layer_name in layer_names
        }
        self._affected_layers_number_l.setText(
            f'Affected layers: {len(affected_layers)}'
        )

    def _on_layer_name_changed(self) -> None:
        self._refresh_display()

    def _on_layer_axis_labels_changed(self) -> None:
        if self._table_model.is_setting_data:
            return
        self._table_model.refresh()

    def _on_viewer_ndim_changed(self) -> None:
        self._table_model.refresh()

    def closeEvent(self, event) -> None:  # type: ignore
        with suppress(TypeError, ValueError, RuntimeError):
            self.ll.selection.events.active.disconnect(
                self._on_layer_selection_changed
            )
        with suppress(TypeError, ValueError, RuntimeError):
            self._viewer_dims.events.ndim.disconnect(
                self._on_viewer_ndim_changed
            )

        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.name.disconnect(
                    self._on_layer_name_changed
                )
            with suppress(TypeError, ValueError, RuntimeError):
                self._event_connected_layer.events.axis_labels.disconnect(
                    self._on_layer_axis_labels_changed
                )

        super().closeEvent(event)
