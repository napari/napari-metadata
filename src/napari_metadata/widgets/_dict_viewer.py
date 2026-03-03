"""
Implement dictionary viewer widget
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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
        self.set_data(data)

    def set_data(self, data: dict | None):
        if data is None:
            data = {}
        self._data = data
        self.tree.clear()
        self.fill_tree(data, self.tree)

    def fill_tree(self, data: dict, parent: QTreeWidget | QTreeWidgetItem):
        for key, value in data.items():
            if isinstance(value, dict):
                key_item = QTreeWidgetItem(parent, [key])
                self.fill_tree(value, key_item)
            elif isinstance(value, list):
                key_item = QTreeWidgetItem(parent, [key])
                for i, val in enumerate(value):
                    self.fill_tree({str(i): val}, key_item)
            else:
                QTreeWidgetItem(parent, [key, str(value)])

    def load_layer_dict(self) -> None:
        self.set_data(get_layer_metadata_dict(self._napari_viewer))
