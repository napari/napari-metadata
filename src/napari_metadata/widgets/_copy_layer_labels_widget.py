from dataclasses import dataclass

from napari.components import Dims, LayerList
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import (
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
        self._rows: list[CopyAxisLabelRow] = []
        self.refresh()

    def refresh(self) -> None:
        self.beginResetModel()
        self._rows = self._build_rows()
        self.endResetModel()

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
        return super().flags(index) & ~Qt.ItemFlag.ItemIsEditable

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
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._model.modelReset.connect(self._on_model_reset)

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
        self.updateGeometry()


class CopyLayerLabelsToAllWidget(QWidget):
    def __init__(
        self, layer_list: LayerList, viewer_dims: Dims, parent_widget: QWidget
    ) -> None:
        super().__init__(parent_widget)
        self.ll = layer_list
        self._viewer_dims = viewer_dims
        self._parent_widget = parent_widget

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

        self.ll.selection.events.active.connect(
            self._on_selected_layer_changed
        )
        self._viewer_dims.events.ndim.connect(self._on_viewer_ndim_changed)
        self._on_selected_layer_changed()

    def _on_selected_layer_changed(self) -> None:
        """Update the template-layer display when active selection changes."""
        active_layer = self.ll.selection.active
        self._layer_l.setText(active_layer.name if active_layer else '')
        self._table_model.refresh()

    def _on_viewer_ndim_changed(self) -> None:
        self._table_model.refresh()
