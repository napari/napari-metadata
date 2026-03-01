"""Concrete file/layer metadata display components.

Each component presents one piece of layer metadata through the
``FileComponentBase`` API defined in ``_base.py``:

* ``LayerName``     — editable layer name (``QLineEdit``)
* ``LayerShape``    — layer data shape (read-only ``QLabel``)
* ``LayerDataType`` — layer data dtype (read-only ``QLabel``)
* ``FileSize``      — file/memory size (read-only ``QLabel``)
* ``SourcePath``    — layer source path (read-only ``QLineEdit``)

``FileGeneralMetadata`` coordinates all five instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QLineEdit, QSizePolicy, QWidget

from napari_metadata.file_size import generate_display_size
from napari_metadata.layer_utils import (
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_source_path,
    resolve_layer,
)
from napari_metadata.widgets._base import FileComponentBase

if TYPE_CHECKING:
    from napari.layers import Layer
    from napari.viewer import ViewerModel


class LayerName(FileComponentBase):
    """Editable layer name using ``QLineEdit``.

    The only file component that writes back to the layer: editing the
    text and pressing Enter renames the layer.
    """

    _label_text = 'Layer Name:'
    _under_label_in_vertical = True

    def __init__(self, viewer: ViewerModel, parent_widget: QWidget) -> None:
        super().__init__(viewer, parent_widget)
        self._line_edit = QLineEdit(parent=parent_widget)
        self._line_edit.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )
        self._line_edit.editingFinished.connect(self._on_name_changed)

    @property
    def value_widget(self) -> QWidget:
        return self._line_edit

    def _get_display_text(self, layer: Layer) -> str:
        return layer.name

    def _update_display(self, layer: Layer | None) -> None:
        if layer is None:
            self._line_edit.setText('None selected')
        else:
            self._line_edit.setText(self._get_display_text(layer))

    def _on_name_changed(self) -> None:
        """Write the edited name back to the active layer."""
        text = self._line_edit.text()
        active_layer = resolve_layer(self._napari_viewer)
        if active_layer is None:
            self._line_edit.setText('No layer selected')
            return
        if text == active_layer.name:
            return
        active_layer.name = text


class LayerShape(FileComponentBase):
    """Read-only layer data shape display."""

    _label_text = 'Layer Shape:'

    def _get_display_text(self, layer: Layer) -> str:
        return str(get_layer_data_shape(layer))


class LayerDataType(FileComponentBase):
    """Read-only layer data dtype display."""

    _label_text = 'Layer DataType:'

    def _get_display_text(self, layer: Layer) -> str:
        return str(get_layer_data_dtype(layer))


class FileSize(FileComponentBase):
    """Read-only file/memory size display."""

    _label_text = 'File Size:'

    def _get_display_text(self, layer: Layer) -> str:
        return str(generate_display_size(layer))


class SourcePath(FileComponentBase):
    """Read-only source path display using a ``QLineEdit``.

    Replaces the old ``SingleLineTextEdit(QTextEdit)`` with a simpler
    read-only ``QLineEdit`` that natively handles single-line scrolling.
    """

    _label_text = 'Source Path:'
    _under_label_in_vertical = True

    def __init__(self, viewer: ViewerModel, parent_widget: QWidget) -> None:
        super().__init__(viewer, parent_widget)
        self._path_line_edit = QLineEdit(parent=parent_widget)
        self._path_line_edit.setReadOnly(True)
        self._path_line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

    @property
    def value_widget(self) -> QWidget:
        return self._path_line_edit

    def _get_display_text(self, layer: Layer) -> str:
        return str(get_layer_source_path(layer))

    def _update_display(self, layer: Layer | None) -> None:
        if layer is None:
            self._path_line_edit.setText('None selected')
        else:
            self._path_line_edit.setText(self._get_display_text(layer))


class FileGeneralMetadata:
    """Coordinator that owns all five file metadata component instances.

    Mirrors the ``AxisMetadata`` coordinator pattern — provides a
    ``components`` property for iteration by ``MetadataWidget``.
    """

    def __init__(self, viewer: ViewerModel, parent_widget: QWidget) -> None:
        self._layer_name = LayerName(viewer, parent_widget)
        self._layer_shape = LayerShape(viewer, parent_widget)
        self._layer_dtype = LayerDataType(viewer, parent_widget)
        self._file_size = FileSize(viewer, parent_widget)
        self._source_path = SourcePath(viewer, parent_widget)

        self._components: list[FileComponentBase] = [
            self._layer_name,
            self._layer_shape,
            self._layer_dtype,
            self._file_size,
            self._source_path,
        ]

    @property
    def components(self) -> list[FileComponentBase]:
        """All file components in display order."""
        return list(self._components)
