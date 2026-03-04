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
    QComboBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from napari_metadata.layer_utils import (
    get_layer_metadata_dict,
    set_layer_metadata_dict,
)
from napari.utils.notifications import show_info

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
        self.tree.setIndentation(28)
        self.tree.setStyleSheet(
            'QTreeWidget::item { padding-top: 4px; padding-bottom: 4px; }'
        )
        self.setMinimumHeight(600)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._selected_items: set[QTreeWidgetItem] = set()
        self._editing_entry = False
        self._editing_widget: KeyWidget | ValueWidget | None = None
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
            items = enumerate(data.items(), start=0)
            for index, (key, value) in items:
                self._fill_tree_item(parent, key, value, index, index_width)
            self._add_dict_add_row(parent, index_width, is_root=True)
        else:
            index_width = getattr(self, '_index_label_width', None)
            items = enumerate(data.items(), start=0)
            for index, (key, value) in items:
                self._fill_tree_item(parent, key, value, index, index_width)
            self._add_dict_add_row(parent, index_width, is_root=False)

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
            key_item.setData(0, Qt.ItemDataRole.UserRole, {'key': key})
            key_item.setData(
                1,
                Qt.ItemDataRole.UserRole,
                {'type': 'dictionary', 'value': value},
            )
            self._set_value_type_widget(key_item, 'dict')
            self.fill_tree(value, key_item)
        elif isinstance(value, (list, tuple)):
            key_item = QTreeWidgetItem(parent, ['', ''])
            self._set_key_widget(key_item, key, index, index_width)
            key_item.setData(0, Qt.ItemDataRole.UserRole, {'key': key})
            key_item.setData(
                1,
                Qt.ItemDataRole.UserRole,
                {
                    'type': 'list' if isinstance(value, list) else 'tuple',
                    'value': value,
                },
            )
            type_name = 'list' if isinstance(value, list) else 'tuple'
            self._set_value_type_widget(key_item, type_name)
            self._fill_sequence_items(value, key_item, index_width, type_name)
        else:
            value_item = QTreeWidgetItem(parent, ['', ''])
            self._set_key_widget(value_item, key, index, index_width)
            value_item.setData(0, Qt.ItemDataRole.UserRole, {'key': key})
            value_widget = ValueWidget(value, self)
            self.tree.setItemWidget(value_item, 1, value_widget)
            self._set_value_item_data(value_item, value)
            self._update_item_height(value_item)

    def load_layer_dict(self) -> None:
        self.set_data(get_layer_metadata_dict(self._napari_viewer))

    def _set_key_widget(
        self,
        item: QTreeWidgetItem,
        key: object,
        index: int | None = None,
        index_width: int | None = None,
    ) -> None:
        key_widget = KeyWidget(
            key, index=index, index_width=index_width, parent=self
        )
        self.tree.setItemWidget(item, 0, key_widget)
        self._update_item_height(item)

    def _set_index_key_widget(
        self,
        item: QTreeWidgetItem,
        index: int,
        entry_type: str,
        index_width: int | None = None,
    ) -> None:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(4)
        label = QLabel(f'[{index}]', container)
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if index_width is not None:
            label.setMinimumWidth(index_width)
        entry_label = QLineEdit(f'{entry_type} entry', container)
        entry_label.setReadOnly(True)
        entry_label.setEnabled(False)
        layout.addWidget(label)
        layout.addWidget(entry_label)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.tree.setItemWidget(item, 0, container)
        item.setData(0, Qt.ItemDataRole.UserRole, {'index': index})
        self._update_item_height(item)

    def _set_add_row_widget(
        self,
        item: QTreeWidgetItem,
        sequence_type: str,
        index_width: int | None,
    ) -> None:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(4)
        add_button = QPushButton('Add', container)
        icon = _load_icon('add.svg')
        if not icon.isNull():
            add_button.setIcon(icon)
            add_button.setText('')
            add_button.setToolTip('Add')
            add_button.setIconSize(QSize(18, 18))
        add_button.setFixedSize(QSize(26, 26))
        entry_label = QLineEdit(f'New {sequence_type} entry', container)
        entry_label.setReadOnly(True)
        entry_label.setEnabled(False)
        layout.addWidget(add_button)
        layout.addWidget(entry_label)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.tree.setItemWidget(item, 0, container)
        item.setData(0, Qt.ItemDataRole.UserRole, {'add_row': True})
        combo_container, value_widgets = self._create_add_value_widget()
        self.tree.setItemWidget(item, 1, combo_container)
        item.setData(
            1, Qt.ItemDataRole.UserRole, {'add_row': True, **value_widgets}
        )
        add_button.clicked.connect(
            lambda: self._add_sequence_entry(item, sequence_type)
        )
        self._update_item_height(item)

    def _create_add_value_widget(self) -> tuple[QWidget, dict]:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(4)
        combo_width = 116
        value_edit = QLineEdit(container)
        type_label = QLabel('', container)
        type_label.setStyleSheet('color: gray; font-style: italic;')
        type_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        combo = QComboBox(container)
        combo.addItems(
            ['number', 'string', 'bool', 'tuple', 'list', 'dictionary', 'none']
        )
        combo.setFixedWidth(combo_width)
        layout.addWidget(value_edit)
        layout.addWidget(type_label)
        layout.addWidget(combo)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        bool_combo = QComboBox(container)
        bool_combo.addItems(['True', 'False'])
        bool_combo.setVisible(False)
        bool_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.insertWidget(1, bool_combo)

        def update_value_widget(selection: str) -> None:
            if selection in ('number', 'string'):
                value_edit.setVisible(True)
                bool_combo.setVisible(False)
                type_label.setVisible(False)
                if value_edit.text() == 'None':
                    value_edit.setText('')
                return
            if selection == 'bool':
                value_edit.setVisible(False)
                bool_combo.setVisible(True)
                type_label.setVisible(False)
                return
            if selection == 'none':
                value_edit.setVisible(False)
                bool_combo.setVisible(False)
                type_label.setText('NA')
                type_label.setVisible(True)
                return
            value_edit.setVisible(False)
            bool_combo.setVisible(False)
            label_text = 'dict' if selection == 'dictionary' else selection
            type_label.setText(label_text)
            type_label.setVisible(True)

        combo.currentTextChanged.connect(update_value_widget)
        update_value_widget(combo.currentText())
        return (
            container,
            {
                'value_edit': value_edit,
                'type_label': type_label,
                'type_combo': combo,
                'bool_combo': bool_combo,
            },
        )

    def _add_dict_add_row(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        index_width: int | None,
        is_root: bool,
    ) -> None:
        add_item = QTreeWidgetItem(parent, ['', ''])
        add_item.setData(0, Qt.ItemDataRole.UserRole, {'add_row': True})
        self._set_dict_add_row_widget(add_item, index_width, is_root)

    def _set_dict_add_row_widget(
        self, item: QTreeWidgetItem, index_width: int | None, is_root: bool
    ) -> None:
        key_container = QWidget(self)
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 16, 0)
        key_layout.setSpacing(4)
        add_button = QPushButton('Add', key_container)
        icon = _load_icon('add.svg')
        if not icon.isNull():
            add_button.setIcon(icon)
            add_button.setText('')
            add_button.setToolTip('Add')
            add_button.setIconSize(QSize(18, 18))
        add_button.setFixedSize(QSize(26, 26))
        key_edit = QLineEdit(key_container)
        key_combo = QComboBox(key_container)
        key_combo.addItems(['number', 'string'])
        key_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        key_layout.addWidget(add_button)
        key_layout.addWidget(key_edit)
        key_layout.addWidget(key_combo)
        key_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.tree.setItemWidget(item, 0, key_container)

        value_container, value_widgets = self._create_add_value_widget()
        self.tree.setItemWidget(item, 1, value_container)
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {
                'add_row': True,
                'key_edit': key_edit,
                'key_combo': key_combo,
            },
        )
        item.setData(
            1, Qt.ItemDataRole.UserRole, {'add_row': True, **value_widgets}
        )
        add_button.clicked.connect(lambda: self._add_dict_entry(item))
        self._update_item_height(item)

    def _fill_sequence_items(
        self,
        values: list | tuple,
        parent: QTreeWidgetItem,
        index_width: int | None,
        sequence_type: str,
    ) -> None:
        for i, val in enumerate(values):
            index_item = QTreeWidgetItem(parent, ['', ''])
            self._set_index_key_widget(
                index_item, i, sequence_type, index_width
            )
            if isinstance(val, dict):
                self._set_value_type_widget(index_item, 'dict')
                self._set_value_item_data(index_item, val)
                self.fill_tree(val, index_item)
            elif isinstance(val, (list, tuple)):
                nested_type = 'list' if isinstance(val, list) else 'tuple'
                self._set_value_type_widget(index_item, nested_type)
                self._set_value_item_data(index_item, val)
                self._fill_sequence_items(
                    val, index_item, index_width, nested_type
                )
            else:
                value_widget = ValueWidget(val, self)
                self.tree.setItemWidget(index_item, 1, value_widget)
                self._set_value_item_data(index_item, val)
                self._update_item_height(index_item)
        add_item = QTreeWidgetItem(parent, ['', ''])
        self._set_add_row_widget(add_item, sequence_type, index_width)

    def _set_value_type_widget(
        self, item: QTreeWidgetItem, type_name: str
    ) -> None:
        value_widget = ValueWidget(None, self, container_type=type_name)
        self.tree.setItemWidget(item, 1, value_widget)
        item.setData(
            1,
            Qt.ItemDataRole.UserRole,
            {'type': 'dictionary' if type_name == 'dict' else type_name},
        )
        self._update_item_height(item)

    def _set_item_selected(
        self, item: QTreeWidgetItem, selected: bool
    ) -> None:
        key_widget = self.tree.itemWidget(item, 0)
        if isinstance(key_widget, KeyWidget):
            key_widget.set_selected(selected)
        value_widget = self.tree.itemWidget(item, 1)
        if isinstance(value_widget, ValueWidget):
            value_widget.set_selected(selected)

    def _iter_items(self) -> list[QTreeWidgetItem]:
        items: list[QTreeWidgetItem] = []
        for i in range(self.tree.topLevelItemCount()):
            items.append(self.tree.topLevelItem(i))
        index = 0
        while index < len(items):
            item = items[index]
            for i in range(item.childCount()):
                items.append(item.child(i))
            index += 1
        return items

    def _find_item_by_widget(
        self, widget: QWidget, column: int
    ) -> QTreeWidgetItem | None:
        for item in self._iter_items():
            if self.tree.itemWidget(item, column) is widget:
                return item
        return None

    def _delete_item_for_widget(self, widget: QWidget, column: int) -> None:
        item = self._find_item_by_widget(widget, column)
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            index = self.tree.indexOfTopLevelItem(item)
            if index >= 0:
                self.tree.takeTopLevelItem(index)
        else:
            index = parent.indexOfChild(item)
            if index >= 0:
                parent.takeChild(index)
        self._recreate_dictionary()

    def _request_edit(self, widget: KeyWidget | ValueWidget) -> None:
        if self._editing_widget is widget:
            return
        if self._editing_widget is not None:
            self._editing_widget.discard_edit()
        self._editing_widget = widget
        self._editing_entry = True

    def _end_edit(self, widget: KeyWidget | ValueWidget) -> None:
        if self._editing_widget is widget:
            self._editing_widget = None
            self._editing_entry = False

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
        if item.parent() is None:
            height += 6
        item.setSizeHint(0, QSize(0, height))
        item.setSizeHint(1, QSize(0, height))

    def _get_index_label_width(self, count: int) -> int:
        digits = max(1, len(str(count)))
        sample = '0' * digits
        metrics = QFontMetrics(self.font())
        return max(metrics.horizontalAdvance(sample) + 10, 24)

    def _set_value_item_data(
        self, item: QTreeWidgetItem, value: object
    ) -> None:
        item.setData(
            1,
            Qt.ItemDataRole.UserRole,
            {'type': self._infer_value_type(value), 'value': value},
        )

    def _get_add_value_spec(self, item: QTreeWidgetItem) -> tuple[str, object]:
        data = item.data(1, Qt.ItemDataRole.UserRole) or {}
        if not isinstance(data, dict):
            return 'string', ''
        type_combo = data.get('type_combo')
        value_edit = data.get('value_edit')
        bool_combo = data.get('bool_combo')
        if type_combo is None:
            return 'string', ''
        selected_type = type_combo.currentText()
        if selected_type == 'number':
            number_value = _parse_number_text(value_edit.text())
            if isinstance(number_value, str):
                return 'invalid', None
            return 'number', number_value
        if selected_type == 'string':
            return 'string', value_edit.text()
        if selected_type == 'bool':
            value = True if bool_combo.currentText() == 'True' else False
            return 'bool', value
        if selected_type == 'none':
            return 'none', None
        if selected_type == 'dictionary':
            return 'dictionary', {}
        if selected_type == 'tuple':
            return 'tuple', ()
        if selected_type == 'list':
            return 'list', []
        return 'string', value_edit.text()

    def _insert_child(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        index: int,
        item: QTreeWidgetItem,
    ) -> None:
        if isinstance(parent, QTreeWidget):
            parent.insertTopLevelItem(index, item)
        else:
            parent.insertChild(index, item)

    def _add_sequence_entry(
        self, add_item: QTreeWidgetItem, sequence_type: str
    ) -> None:
        parent = add_item.parent()
        if parent is None:
            return
        index_width = getattr(self, '_index_label_width', None)
        insert_index = parent.indexOfChild(add_item)
        entry_index = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            if self._is_add_row(child):
                continue
            entry_index += 1
        value_type, value = self._get_add_value_spec(add_item)
        if value_type == 'invalid':
            return
        new_item = QTreeWidgetItem(['', ''])
        self._insert_child(parent, insert_index, new_item)
        self._set_index_key_widget(
            new_item, entry_index, sequence_type, index_width
        )
        if value_type == 'dictionary':
            self._set_value_type_widget(new_item, 'dict')
            self._set_value_item_data(new_item, value)
            self.fill_tree(value, new_item)
        elif value_type == 'list':
            self._set_value_type_widget(new_item, 'list')
            self._set_value_item_data(new_item, value)
            self._fill_sequence_items(value, new_item, index_width, 'list')
        elif value_type == 'tuple':
            self._set_value_type_widget(new_item, 'tuple')
            self._set_value_item_data(new_item, value)
            self._fill_sequence_items(value, new_item, index_width, 'tuple')
        else:
            value_widget = ValueWidget(value, self)
            self.tree.setItemWidget(new_item, 1, value_widget)
            self._set_value_item_data(new_item, value)
            self._update_item_height(new_item)
        self._recreate_dictionary()

    def _add_dict_entry(self, add_item: QTreeWidgetItem) -> None:
        parent = add_item.parent() or self.tree
        data = add_item.data(0, Qt.ItemDataRole.UserRole) or {}
        if not isinstance(data, dict):
            return
        key_edit = data.get('key_edit')
        key_combo = data.get('key_combo')
        if key_edit is None or key_combo is None:
            return
        key_text = key_edit.text()
        if key_text == '':
            return
        if key_combo.currentText() == 'number':
            key_value = _parse_number_text(key_text)
            if isinstance(key_value, str):
                return
        else:
            key_value = key_text
        for i in range(
            parent.childCount()
            if isinstance(parent, QTreeWidgetItem)
            else self.tree.topLevelItemCount()
        ):
            child = (
                parent.child(i)
                if isinstance(parent, QTreeWidgetItem)
                else self.tree.topLevelItem(i)
            )
            if self._is_add_row(child):
                continue
            existing_key = child.data(0, Qt.ItemDataRole.UserRole) or {}
            if isinstance(existing_key, dict):
                existing_key = existing_key.get('key')
            if existing_key == key_value:
                show_info(f'Key already exists in this dictionary: {existing_key}')
                return
        index_width = getattr(self, '_index_label_width', None)
        insert_index = (
            parent.indexOfChild(add_item)
            if isinstance(parent, QTreeWidgetItem)
            else self.tree.indexOfTopLevelItem(add_item)
        )
        value_type, value = self._get_add_value_spec(add_item)
        if value_type == 'invalid':
            return
        new_item = QTreeWidgetItem(['', ''])
        if isinstance(parent, QTreeWidget):
            parent.insertTopLevelItem(insert_index, new_item)
        else:
            parent.insertChild(insert_index, new_item)
        self._set_key_widget(new_item, key_value, insert_index, index_width)
        new_item.setData(0, Qt.ItemDataRole.UserRole, {'key': key_value})
        if value_type == 'dictionary':
            self._set_value_type_widget(new_item, 'dict')
            self._set_value_item_data(new_item, value)
            self.fill_tree(value, new_item)
        elif value_type == 'list':
            self._set_value_type_widget(new_item, 'list')
            self._set_value_item_data(new_item, value)
            self._fill_sequence_items(value, new_item, index_width, 'list')
        elif value_type == 'tuple':
            self._set_value_type_widget(new_item, 'tuple')
            self._set_value_item_data(new_item, value)
            self._fill_sequence_items(value, new_item, index_width, 'tuple')
        else:
            value_widget = ValueWidget(value, self)
            self.tree.setItemWidget(new_item, 1, value_widget)
            self._set_value_item_data(new_item, value)
            self._update_item_height(new_item)
        self._recreate_dictionary()

    def _infer_value_type(self, value: object) -> str:
        if value is None:
            return 'none'
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, str):
            return 'string'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return 'number'
        if isinstance(value, dict):
            return 'dictionary'
        if isinstance(value, list):
            return 'list'
        if isinstance(value, tuple):
            return 'tuple'
        return 'other'

    def _is_add_row(self, item: QTreeWidgetItem) -> bool:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return isinstance(data, dict) and data.get('add_row', False)

    def _recreate_dictionary(self) -> None:
        def parse_key(item: QTreeWidgetItem) -> object:
            key_widget = self.tree.itemWidget(item, 0)
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if not isinstance(key_widget, KeyWidget):
                return data.get('key')
            if not key_widget.was_edited():
                if hasattr(key_widget, 'key_edit'):
                    return data.get('key', key_widget.key_edit.text())
                return data.get('key')
            if hasattr(key_widget, 'key_edit'):
                key_text = key_widget.key_edit.text()
            else:
                key_text = key_widget.key_label.text()
            key_type = key_widget.type_label.text().lower()
            if key_type == 'number':
                return _parse_number_text(key_text)
            if key_type == 'non-editable':
                return data.get('key', key_text)
            return key_text

        def parse_value(item: QTreeWidgetItem) -> object:
            value_widget = self.tree.itemWidget(item, 1)
            if isinstance(value_widget, ValueWidget):
                value_type = value_widget.get_type()
                if value_type in ('dictionary', 'list', 'tuple'):
                    return parse_container(item, value_type)
                if not value_widget.was_edited():
                    data = item.data(1, Qt.ItemDataRole.UserRole) or {}
                    if isinstance(data, dict) and 'value' in data:
                        return data['value']
                if value_type == 'other':
                    data = item.data(1, Qt.ItemDataRole.UserRole) or {}
                    if isinstance(data, dict) and 'value' in data:
                        return data['value']
                return value_widget.get_value()
            data = item.data(1, Qt.ItemDataRole.UserRole) or {}
            if isinstance(data, dict) and 'value' in data:
                return data['value']
            return None

        def parse_container(
            item: QTreeWidgetItem, container_type: str
        ) -> object:
            if container_type == 'dictionary':
                result: dict = {}
                for i in range(item.childCount()):
                    child = item.child(i)
                    if self._is_add_row(child):
                        continue
                    key = parse_key(child)
                    result[key] = parse_value(child)
                return result
            values = []
            for i in range(item.childCount()):
                child = item.child(i)
                if self._is_add_row(child):
                    continue
                values.append(parse_value(child))
            return tuple(values) if container_type == 'tuple' else values

        result: dict = {}
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if self._is_add_row(item):
                continue
            key = parse_key(item)
            result[key] = parse_value(item)
        set_layer_metadata_dict(self._napari_viewer, None, result)
        self.load_layer_dict()


class KeyWidget(QWidget):
    key_changed = Signal(str, str)

    def __init__(
        self,
        key: object,
        index: int | None = None,
        index_width: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._viewer = (
            parent if isinstance(parent, MetadataDictViewer) else None
        )
        self._original_key = str(key)
        self._is_editable = isinstance(key, str) or (
            isinstance(key, (int, float)) and not isinstance(key, bool)
        )
        self._type_label_color: str | None = None
        self._edit_icon = _load_icon('edit.svg')
        self._confirm_icon = _load_icon('confirm.svg')
        self._discarding = False
        self._edited = False
        self._bool_combo: QComboBox | None = None
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 16, 0)
        self._layout.setSpacing(4)
        if index is not None:
            self.index_label = QLabel(f'[{index}]', self)
            if index_width is not None:
                self.index_label.setFixedWidth(index_width)
            self._layout.addWidget(self.index_label)
        elif index_width is not None:
            spacer = QLabel('', self)
            spacer.setFixedWidth(index_width)
            self._layout.addWidget(spacer)
        self.key_edit = QLineEdit(self._original_key, self)
        self.key_edit.setReadOnly(True)
        if isinstance(key, str):
            type_text = 'string'
            self._type_label_color = '#e68c2c'
        elif isinstance(key, (int, float)) and not isinstance(key, bool):
            type_text = 'number'
            self._type_label_color = '#4091ed'
        else:
            type_text = 'NE'
        self._original_type = type_text
        self.type_combo = QComboBox(self)
        self.type_combo.addItems(['number', 'string'])
        self.type_combo.setVisible(False)
        self.delete_button = QPushButton('Delete', self)
        self.delete_button.setCheckable(True)
        self.type_label = QLabel(type_text, self)
        if self._is_editable and self._type_label_color is not None:
            self.type_label.setStyleSheet(f'color: {self._type_label_color};')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
        else:
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            self.type_label.setFixedWidth(56)
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.edit_button.setCheckable(True)
        self._apply_icon(self.edit_button, 'edit.svg', 'Edit', QSize(14, 14))
        self._apply_icon(
            self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
        )
        self._layout.addWidget(self.key_edit)
        self.edit_button.toggled.connect(self._on_edit_toggled)
        self._layout.addWidget(self.type_label)
        self._layout.addWidget(self.type_combo)
        self._layout.addWidget(self.edit_button)
        self._layout.addWidget(self.delete_button)
        self.delete_button.clicked.connect(self._on_delete_clicked)

    def _on_edit_toggled(self, checked: bool) -> None:
        if checked and self._viewer is not None:
            self._viewer._request_edit(self)
        self.key_edit.setReadOnly(not checked)
        self.type_label.setVisible(not checked)
        self.type_combo.setVisible(checked)
        self.delete_button.setVisible(not checked)
        if checked:
            current_type = self._original_type
            if current_type not in ('number', 'string'):
                current_type = 'string'
            self.type_combo.setCurrentText(current_type)
            if not self._confirm_icon.isNull():
                self.edit_button.setIcon(self._confirm_icon)
            self._apply_icon(
                self.delete_button, 'cancel.svg', 'Cancel', QSize(18, 18)
            )
            self.delete_button.setToolTip('Cancel edit')
            self.delete_button.setChecked(True)
            self.delete_button.setVisible(True)
        else:
            if not self._edit_icon.isNull():
                self.edit_button.setIcon(self._edit_icon)
            self._apply_icon(
                self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
            )
            self.delete_button.setToolTip('Delete')
            self.delete_button.setChecked(False)
            if self._discarding:
                self._discarding = False
                self.key_edit.setText(self._original_key)
                self.type_combo.setVisible(False)
                self.type_label.setVisible(True)
                return
            self._commit_edit()
            if self._viewer is not None:
                self._viewer._end_edit(self)

    def _on_cancel_clicked(self) -> None:
        if not self.edit_button.isChecked():
            return
        self.discard_edit()
        self._apply_icon(
            self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
        )
        if self._viewer is not None:
            self._viewer._end_edit(self)

    def _on_delete_clicked(self) -> None:
        if self.edit_button.isChecked():
            self._on_cancel_clicked()
            return
        if self._viewer is not None:
            self._viewer._delete_item_for_widget(self, 0)

    def _commit_edit(self) -> None:
        new_key = self.key_edit.text()
        selected_type = self.type_combo.currentText()
        if selected_type == 'number':
            try:
                float(new_key)
            except ValueError:
                self.key_edit.setText(self._original_key)
                self.type_combo.setCurrentText(self._original_type)
                self._apply_type_selection(self._original_type)
                return
        if new_key == self._original_key:
            self._apply_type_selection(selected_type)
            return
        old_key = self._original_key
        self._original_key = new_key
        self.key_changed.emit(old_key, new_key)
        self._apply_type_selection(selected_type)
        self._edited = True
        if self._viewer is not None:
            self._viewer._recreate_dictionary()
            self._viewer._end_edit(self)

    def _apply_type_selection(self, selected_type: str | None = None) -> None:
        if selected_type is None:
            selected_type = self.type_combo.currentText()
        if selected_type == 'string':
            self._type_label_color = '#e68c2c'
        else:
            self._type_label_color = '#4091ed'
        self._original_type = selected_type
        self.type_label.setText(selected_type)
        self.type_label.setStyleSheet(f'color: {self._type_label_color};')
        self.type_label.setVisible(True)
        self.type_combo.setVisible(False)

    def discard_edit(self) -> None:
        self._discarding = True
        self.edit_button.setChecked(False)
        self.key_edit.setText(self._original_key)
        self.key_edit.setReadOnly(True)
        self.type_combo.setVisible(False)
        if self._original_type in ('string', 'number'):
            self._apply_type_selection(self._original_type)
        else:
            self.type_label.setText('NE')
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            self.type_label.setVisible(True)
        if not self._edit_icon.isNull():
            self.edit_button.setIcon(self._edit_icon)

    def was_edited(self) -> bool:
        return self._edited

    def set_selected(self, selected: bool) -> None:
        if self._is_editable and self._type_label_color is not None:
            if selected:
                self.type_label.setStyleSheet('color: black;')
            else:
                self.type_label.setStyleSheet(
                    f'color: {self._type_label_color};'
                )
            return
        if selected:
            self.type_label.setStyleSheet('color: black; font-style: italic;')
        else:
            self.type_label.setStyleSheet('color: gray; font-style: italic;')

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
    def __init__(
        self,
        value: object,
        parent: QWidget | None = None,
        container_type: str | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._viewer = (
            parent if isinstance(parent, MetadataDictViewer) else None
        )
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 0, 0, 0)
        self._layout.setSpacing(4)
        self._editable = False
        self._type_label_color: str | None = None
        self._original_value_text: str | None = None
        self._original_type_text: str | None = None
        self._edit_icon = _load_icon('edit.svg')
        self._confirm_icon = _load_icon('confirm.svg')
        self._discarding = False
        self._edited = False

        if container_type is not None:
            self.value_edit = QLineEdit('', self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('', self)
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
            type_mapping = {
                'dict': 'dictionary',
                'list': 'list',
                'tuple': 'tuple',
            }
            self._original_value_text = ''
            self._original_type_text = type_mapping.get(container_type, 'list')
            self._apply_value_display(self._original_type_text)
        elif isinstance(value, str):
            self.value_edit = QLineEdit(value, self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('string', self)
            self._type_label_color = '#e68c2c'
            self.type_label.setStyleSheet(f'color: {self._type_label_color};')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
            self._original_value_text = value
            self._original_type_text = 'string'
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            self.value_edit = QLineEdit(str(value), self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('number', self)
            self._type_label_color = '#4091ed'
            self.type_label.setStyleSheet(f'color: {self._type_label_color};')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
            self._original_value_text = str(value)
            self._original_type_text = 'number'
        elif isinstance(value, bool):
            self.value_edit = QLineEdit(str(value), self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('bool', self)
            self.type_label.setStyleSheet('color: #bf3be3;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
            self._original_value_text = str(value)
            self._original_type_text = 'bool'
        elif value is None:
            self.value_edit = QLineEdit('None', self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('NA', self)
            self.type_label.setStyleSheet('color: black;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self.delete_button.setEnabled(False)
            self._editable = True
            self._original_value_text = 'None'
            self._original_type_text = 'none'
        else:
            self.value_edit = QLineEdit(str(value), self)
            self.value_edit.setReadOnly(True)
            self.type_label = QLabel('NE', self)
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setFixedWidth(56)
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            self._layout.addWidget(self.value_edit)
            self._layout.addWidget(self.type_label)
            self._add_controls(editable=True)
            self._editable = True
            self._original_value_text = str(value)
            self._original_type_text = 'other'

    def set_selected(self, selected: bool) -> None:
        if self._editable and self._type_label_color is not None:
            if selected:
                self.type_label.setStyleSheet('color: black;')
            else:
                self.type_label.setStyleSheet(
                    f'color: {self._type_label_color};'
                )
            return
        if selected:
            self.type_label.setStyleSheet('color: black; font-style: italic;')
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setStyleSheet(
                    'color: black; font-style: italic;'
                )
        else:
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setStyleSheet(
                    'color: gray; font-style: italic;'
                )

    def _add_controls(self, editable: bool) -> None:
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.setCheckable(True)
        self.edit_button.setVisible(editable)
        self.delete_button = QPushButton('Delete', self)
        self.delete_button.setCheckable(True)
        self._apply_icon(self.edit_button, 'edit.svg', 'Edit', QSize(14, 14))
        self._apply_icon(
            self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
        )
        self._layout.addWidget(self.edit_button)
        self._layout.addWidget(self.delete_button)
        if editable:
            self.type_combo = QComboBox(self)
            self.type_combo.addItems(
                [
                    'number',
                    'string',
                    'bool',
                    'tuple',
                    'list',
                    'dictionary',
                    'none',
                ]
            )
            self.type_combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToContents
            )
            self.type_combo.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
            )
            self._bool_combo = QComboBox(self)
            self._bool_combo.addItems(['True', 'False'])
            self._bool_combo.setVisible(False)
            self._bool_combo.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self.type_combo.setVisible(False)
            self._layout.insertWidget(1, self._bool_combo)
            self._layout.insertWidget(2, self.type_combo)
            self.edit_button.toggled.connect(self._on_edit_toggled)
            self.type_combo.currentTextChanged.connect(
                self._apply_value_type_selection
            )
        self.delete_button.clicked.connect(self._on_delete_clicked)

    def _on_edit_toggled(self, checked: bool) -> None:
        if checked and self._viewer is not None:
            self._viewer._request_edit(self)
        self.value_edit.setReadOnly(not checked)
        self.type_label.setVisible(not checked)
        self.type_combo.setVisible(checked)
        self.delete_button.setVisible(not checked)
        if checked:
            current_type = (
                self._original_type_text or self.type_label.text().lower()
            )
            if current_type == 'na':
                current_type = 'none'
            elif current_type == 'non-editable':
                current_type = 'string'
            valid_types = {
                'number',
                'string',
                'bool',
                'tuple',
                'list',
                'dictionary',
                'none',
            }
            if current_type in valid_types:
                self.type_combo.setCurrentText(current_type)
                self._apply_value_type_selection(current_type)
            else:
                self.type_combo.setCurrentText('string')
            if not self._confirm_icon.isNull():
                self.edit_button.setIcon(self._confirm_icon)
            self._apply_icon(
                self.delete_button, 'cancel.svg', 'Cancel', QSize(18, 18)
            )
            self.delete_button.setToolTip('Cancel edit')
            self.delete_button.setChecked(True)
            self.delete_button.setEnabled(True)
            self.delete_button.setVisible(True)
        else:
            if not self._edit_icon.isNull():
                self.edit_button.setIcon(self._edit_icon)
            self._apply_icon(
                self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
            )
            self.delete_button.setToolTip('Delete')
            self.delete_button.setChecked(False)
            if self._discarding:
                self._discarding = False
                if self._original_type_text is not None:
                    self._apply_value_display(self._original_type_text)
                return
            self._commit_edit()
            self._apply_value_display(self.type_combo.currentText())
            if self._viewer is not None:
                self._viewer._end_edit(self)

    def _on_cancel_clicked(self) -> None:
        if not self._editable:
            return
        if not self.edit_button.isChecked():
            return
        self.discard_edit()
        self._apply_icon(
            self.delete_button, 'delete.svg', 'Delete', QSize(18, 18)
        )
        if self._viewer is not None:
            self._viewer._end_edit(self)

    def _on_delete_clicked(self) -> None:
        if not self._editable:
            return
        if self.edit_button.isChecked():
            self._on_cancel_clicked()
            return
        if self._viewer is not None:
            self._viewer._delete_item_for_widget(self, 1)

    def _apply_value_type_selection(self, selected_type: str) -> None:
        if hasattr(self, 'value_label') and self.value_label is not None:
            self.value_label.setVisible(False)
        if selected_type in ('string', 'number'):
            self.value_edit.setVisible(True)
            self.value_edit.setReadOnly(False)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if self.value_edit.text() in (
                'new tuple',
                'new list',
                'new dict',
                'None',
            ):
                self.value_edit.setText('')
            self.type_label.setVisible(False)
            return
        if selected_type == 'bool':
            self.value_edit.setVisible(False)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(True)
                if self._original_value_text in ('True', 'False'):
                    self._bool_combo.setCurrentText(self._original_value_text)
            self.type_label.setVisible(False)
            return
        self.value_edit.setReadOnly(True)
        self.value_edit.setVisible(True)
        if self._bool_combo is not None:
            self._bool_combo.setVisible(False)
        if selected_type == 'dictionary':
            self.value_edit.setText('new dict')
        elif selected_type == 'tuple':
            self.value_edit.setText('new tuple')
        elif selected_type == 'list':
            self.value_edit.setText('new list')
        else:
            self.value_edit.setText('None')
        self.type_label.setVisible(False)

    def _apply_value_display(self, selected_type: str) -> None:
        self.value_edit.setReadOnly(True)
        if selected_type == 'string':
            self.value_edit.setVisible(True)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setVisible(False)
            self.type_label.setText('string')
            self.type_label.setStyleSheet('color: #e68c2c;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setVisible(True)
            self.delete_button.setEnabled(True)
        elif selected_type == 'other':
            self.value_edit.setVisible(True)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setVisible(False)
            if self._original_value_text is not None:
                self.value_edit.setText(self._original_value_text)
            self.type_label.setText('NE')
            self.type_label.setStyleSheet('color: gray; font-style: italic;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setVisible(True)
            self.delete_button.setEnabled(True)
        elif selected_type == 'number':
            self.value_edit.setVisible(True)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setVisible(False)
            self.type_label.setText('number')
            self.type_label.setStyleSheet('color: #4091ed;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setVisible(True)
            self.delete_button.setEnabled(True)
        elif selected_type == 'bool':
            self.value_edit.setVisible(False)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if not hasattr(self, 'value_label') or self.value_label is None:
                self.value_label = QLabel(self)
                self.value_label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self._layout.insertWidget(0, self.value_label)
            label_text = (
                self._original_value_text
                if self._original_value_text in ('True', 'False')
                else 'False'
            )
            self.value_label.setText(label_text)
            self.value_label.setStyleSheet('color: gray; font-style: italic;')
            self.value_label.setVisible(True)
            self.type_label.setText('bool')
            self.type_label.setStyleSheet('color: #bf3be3;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setVisible(True)
            self.delete_button.setEnabled(True)
        elif selected_type in ('dictionary', 'tuple', 'list'):
            self.value_edit.setVisible(False)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if not hasattr(self, 'value_label') or self.value_label is None:
                self.value_label = QLabel(self)
                self.value_label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self._layout.insertWidget(0, self.value_label)
            label_text = (
                'dict'
                if selected_type == 'dictionary'
                else 'tuple'
                if selected_type == 'tuple'
                else 'list'
            )
            self.value_label.setText(label_text)
            self.value_label.setStyleSheet('color: gray; font-style: italic;')
            self.value_label.setVisible(True)
            self.type_label.setVisible(False)
            self.delete_button.setEnabled(True)
        else:
            self.value_edit.setVisible(True)
            if self._bool_combo is not None:
                self._bool_combo.setVisible(False)
            if hasattr(self, 'value_label') and self.value_label is not None:
                self.value_label.setVisible(False)
            self.value_edit.setText('None')
            self.type_label.setText('NA')
            self.type_label.setStyleSheet('color: black;')
            self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.type_label.setVisible(True)
            self.delete_button.setEnabled(False)

    def discard_edit(self) -> None:
        if not self._editable:
            return
        self._discarding = True
        self.edit_button.setChecked(False)
        if self._original_value_text is not None:
            self.value_edit.setText(self._original_value_text)
        if self._original_type_text is not None:
            self.type_combo.setCurrentText(self._original_type_text)
        if self._bool_combo is not None and self._original_value_text in (
            'True',
            'False',
        ):
            self._bool_combo.setCurrentText(self._original_value_text)
        self.value_edit.setReadOnly(True)
        self.type_combo.setVisible(False)
        if self._original_type_text is not None:
            self._apply_value_display(self._original_type_text)
        else:
            self.type_label.setVisible(True)
        if not self._edit_icon.isNull():
            self.edit_button.setIcon(self._edit_icon)

    def _commit_edit(self) -> None:
        if (
            self._original_value_text is None
            or self._original_type_text is None
        ):
            return
        selected_type = self.type_combo.currentText()
        if selected_type == 'number':
            try:
                float(self.value_edit.text())
            except ValueError:
                self.value_edit.setText(self._original_value_text)
                self.type_combo.setCurrentText(self._original_type_text)
                return
        if selected_type == 'bool':
            if self._bool_combo is not None:
                self._original_value_text = self._bool_combo.currentText()
            else:
                self._original_value_text = 'False'
            self._original_type_text = 'bool'
            self._edited = True
            if self._viewer is not None:
                self._viewer._recreate_dictionary()
            return
        self._original_value_text = self.value_edit.text()
        self._original_type_text = selected_type
        self._edited = True
        if self._viewer is not None:
            self._viewer._recreate_dictionary()

    def was_edited(self) -> bool:
        return self._edited

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

    def get_type(self) -> str:
        if self._original_type_text is None:
            return 'other'
        return self._original_type_text

    def get_value(self) -> object:
        value_type = self.get_type()
        if value_type == 'none':
            return None
        if value_type == 'number':
            return _parse_number_text(self.value_edit.text())
        if value_type == 'string':
            return self.value_edit.text()
        if value_type == 'bool':
            text_value = (
                self._original_value_text
                if self._original_value_text in ('True', 'False')
                else self.value_edit.text()
            )
            return text_value == 'True'
        if hasattr(self, 'value_edit'):
            return self.value_edit.text()
        if hasattr(self, 'value_label'):
            return self.value_label.text()
        return None


def _load_icon(name: str) -> QIcon:
    try:
        icon_path = (
            resources.files('napari_metadata') / 'resources' / 'icons' / name
        )
    except Exception:
        return QIcon()
    if not icon_path.is_file():
        return QIcon()
    return QIcon(str(icon_path))


def _parse_number_text(text: str) -> int | float | str:
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text
