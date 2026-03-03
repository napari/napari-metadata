"""
Implement dictionary viewer widget
"""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING

from qtpy.QtCore import Signal, QSize, Qt
from qtpy.QtGui import QFontMetrics, QIcon
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from napari_metadata.layer_utils import get_layer_metadata_dict

if TYPE_CHECKING:
    from napari.components import ViewerModel


class MetadataDictViewer(QWidget):
    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent: QWidget,
        data: dict | None = None,
    ):
        super().__init__(parent=parent)
        self._napari_viewer = napari_viewer
        self._data = {}
        self.tree = QTreeWidget(parent=self)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.tree)
        self.setLayout(self._layout)
        self.tree.setHeaderLabels(['Key', 'Value'])
        self.tree.setStyleSheet(
            'QTreeWidget::item { padding-top: 4px; padding-bottom: 4px; }'
        )
        self.setMinimumHeight(600)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._selected_items: set[QTreeWidgetItem] = set()
        self.tree.itemSelectionChanged.connect(self._on_item_selection_changed)
        self.set_data(data)

    def set_data(self, data: dict | None):
        if data is None:
            data = {}
        self._data = data
        self.tree.clear()
        self.fill_tree(data, self.tree)

    def fill_tree(self, data: dict, parent: QTreeWidget | QTreeWidgetItem):
        is_root = parent is self.tree
        if is_root:
            index_width = self._get_index_label_width(len(data))
            self._index_label_width = index_width
            items = enumerate(data.items(), start=1)
            for index, (key, value) in items:
                self._fill_tree_item(parent, key, value, index, index_width)
        else:
            index_width = getattr(self, '_index_label_width', None)
            for key, value in data.items():
                self._fill_tree_item(parent, key, value, None, index_width)

    def _fill_tree_item(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        key: str,
        value: object,
        index: int | None,
        index_width: int | None,
    ) -> None:
        if isinstance(value, dict):
            key_item = QTreeWidgetItem(parent, ['', ''])
            self._set_key_widget(key_item, key, index, index_width)
            self.fill_tree(value, key_item)
        elif isinstance(value, list):
            key_item = QTreeWidgetItem(parent, ['', ''])
            self._set_key_widget(key_item, key, index, index_width)
            for i, val in enumerate(value):
                self.fill_tree({str(i): val}, key_item)
        else:
            value_item = QTreeWidgetItem(parent, ['', ''])
            self._set_key_widget(value_item, key, index, index_width)
            value_widget = ValueWidget(value, self)
            self.tree.setItemWidget(value_item, 1, value_widget)
            self._update_item_height(value_item)

    def load_layer_dict(self) -> None:
        self.set_data(get_layer_metadata_dict(self._napari_viewer))

    def _set_key_widget(
        self,
        item: QTreeWidgetItem,
        key: str,
        index: int | None = None,
        index_width: int | None = None,
    ) -> None:
        key_widget = KeyWidget(
            str(key), index=index, index_width=index_width, parent=self
        )
        self.tree.setItemWidget(item, 0, key_widget)
        self._update_item_height(item)

    def _set_item_selected(
        self, item: QTreeWidgetItem, selected: bool
    ) -> None:
        value_widget = self.tree.itemWidget(item, 1)
        if isinstance(value_widget, ValueWidget):
            value_widget.set_selected(selected)

    def _on_item_selection_changed(self) -> None:
        current = set(self.tree.selectedItems())
        for item in self._selected_items - current:
            self._set_item_selected(item, False)
        for item in current - self._selected_items:
            self._set_item_selected(item, True)
        self._selected_items = current

    def _update_item_height(self, item: QTreeWidgetItem) -> None:
        heights = []
        for column in (0, 1):
            widget = self.tree.itemWidget(item, column)
            if widget is not None:
                heights.append(widget.sizeHint().height())
        if not heights:
            return
        height = max(heights) + 8
        item.setSizeHint(0, QSize(0, height))
        item.setSizeHint(1, QSize(0, height))

    def _get_index_label_width(self, count: int) -> int:
        digits = max(1, len(str(count)))
        sample = '0' * digits
        metrics = QFontMetrics(self.font())
        return max(metrics.horizontalAdvance(sample) + 10, 24)


class KeyWidget(QWidget):
    key_changed = Signal(str, str)

    def __init__(
        self,
        key: str,
        index: int | None = None,
        index_width: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._original_key = key
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(4)
        if index is not None:
            self.index_label = QLabel(str(index), self)
            if index_width is not None:
                self.index_label.setFixedWidth(index_width)
            self._layout.addWidget(self.index_label)
        elif index_width is not None:
            spacer = QLabel('', self)
            spacer.setFixedWidth(index_width)
            self._layout.addWidget(spacer)
        self.key_edit = QLineEdit(key, self)
        self.key_edit.setReadOnly(True)
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.setCheckable(True)
        self.delete_button = QPushButton('Delete', self)
        self._apply_icon(self.edit_button, 'edit.svg', 'Edit', QSize(14, 14))
        self._apply_icon(self.delete_button, 'delete.svg', 'Delete', QSize(18, 18))
        self._layout.addWidget(self.edit_button)
        self._layout.addWidget(self.delete_button)
        self._layout.addWidget(self.key_edit)
        self.key_edit.editingFinished.connect(self._on_editing_finished)
        self.edit_button.toggled.connect(
            lambda checked: self.key_edit.setReadOnly(not checked)
        )

    def _on_editing_finished(self) -> None:
        new_key = self.key_edit.text()
        if new_key == self._original_key:
            return
        old_key = self._original_key
        self._original_key = new_key
        self.key_changed.emit(old_key, new_key)

    def _apply_icon(
        self,
        button: QPushButton,
        icon_name: str,
        tooltip: str,
        icon_size: QSize,
    ) -> None:
        icon = _load_icon(icon_name)
        if not icon.isNull():
            button.setIcon(icon)
            button.setText('')
            button.setToolTip(tooltip)
            button.setIconSize(icon_size)
        button.setFixedSize(QSize(26, 26))


class ValueWidget(QWidget):
    def __init__(self, value: object, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 0, 0, 0)
        self._layout.setSpacing(4)
        self._editable = False

        if isinstance(value, str):
            self.value_edit = QLineEdit(value, self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('string', self)
            self.type_label.setStyleSheet('color: #e68c2c;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            self.value_edit = QLineEdit(str(value), self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('number', self)
            self.type_label.setStyleSheet('color: #4091ed;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
        else:
            self.value_label = QLabel(str(value), self)
            self.type_label = QLabel('Non-editable', self)
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.type_label.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            self._layout.addWidget(self.value_label)
            self._layout.addWidget(
                self.type_label, alignment=Qt.AlignmentFlag.AlignVCenter
            )
            self._add_controls(editable=False)

    def set_selected(self, selected: bool) -> None:
        if self._editable:
            return
        if selected:
            self.type_label.setStyleSheet('color: black; font-style: italic;')
        else:
            self.type_label.setStyleSheet('color: gray; font-style: italic;')

    def _add_controls(self, editable: bool) -> None:
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.setCheckable(True)
        self.edit_button.setVisible(editable)
        self.delete_button = QPushButton('Delete', self)
        self._apply_icon(self.edit_button, 'edit.svg', 'Edit', QSize(14, 14))
        self._apply_icon(self.delete_button, 'delete.svg', 'Delete', QSize(18, 18))
        self._layout.addWidget(self.edit_button)
        self._layout.addWidget(self.delete_button)
        if editable:
            self.edit_button.toggled.connect(
                lambda checked: self.value_edit.setReadOnly(not checked)
            )

    def _apply_icon(
        self,
        button: QPushButton,
        icon_name: str,
        tooltip: str,
        icon_size: QSize,
    ) -> None:
        icon = _load_icon(icon_name)
        if not icon.isNull():
            button.setIcon(icon)
            button.setText('')
            button.setToolTip(tooltip)
            button.setIconSize(icon_size)
        button.setFixedSize(QSize(26, 26))


def _load_icon(name: str) -> QIcon:
    try:
        icon_path = resources.files('napari_metadata') / 'resources' / 'icons' / name
    except Exception:
        return QIcon()
    if not icon_path.is_file():
        return QIcon()
    return QIcon(str(icon_path))
