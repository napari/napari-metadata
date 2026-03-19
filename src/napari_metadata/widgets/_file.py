"""Concrete file/layer metadata display components.

Each component presents one piece of layer metadata through the
``FileComponentBase`` API defined in ``_base.py``:

* ``LayerName``          — editable layer name (``QLineEdit``)
* ``LayerShape``         — layer data shape (read-only ``QLabel``)
* ``LayerDataType``      — layer data dtype (read-only ``QLabel``)
* ``FileSize``           — file/memory size (read-only ``QLabel``)
* ``SourcePath``         — source path, hidden when ``None`` (``QLineEdit``)
* ``SourceReaderPlugin`` — reader plugin name, hidden when ``None``
* ``SourceSample``       — sample data id, hidden when ``None``
* ``SourceWidget``       — source widget name, hidden when ``None``
* ``SourceParent``       — source parent layer, hidden when ``None``

The five source-related components are hidden automatically when their
corresponding ``layer.source`` attribute is ``None``.

``FileGeneralMetadata`` coordinates all nine instances.
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from qtpy.QtWidgets import QLineEdit, QSizePolicy, QWidget

from napari_metadata.file_size import generate_display_size
from napari_metadata.layer_utils import (
    get_layer_data_dtype,
    get_layer_data_shape,
)
from napari_metadata.widgets._base import FileComponentBase

if TYPE_CHECKING:
    from napari.layers import Layer


class LayerName(FileComponentBase):
    """Editable layer name using ``QLineEdit``.

    The only file component that writes back to the layer: editing the
    text and pressing Enter renames the layer.
    """

    _label_text = 'Layer Name:'
    _under_label_in_vertical = True

    #: The layer currently loaded.  Set by ``load_entries``; valid whenever
    #: ``_on_name_changed`` runs (the signal is only reachable after
    #: ``load_entries`` has been called).
    #: **Do not access before the first** ``load_entries`` **call.**
    _selected_layer: Layer

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
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

    def load_entries(self, layer: Layer) -> None:
        self._selected_layer = layer
        super().load_entries(layer)

    def clear(self) -> None:
        self._line_edit.setText('')

    def _get_display_text(self, layer: Layer) -> str:
        return layer.name

    def _update_display(self, layer: Layer) -> None:
        self._line_edit.setText(self._get_display_text(layer))

    def _on_name_changed(self) -> None:
        """Write the edited name back to the active layer."""
        text = self._line_edit.text()
        if text == self._selected_layer.name:
            return
        self._selected_layer.name = text


class LayerShape(FileComponentBase):
    """Read-only layer data shape display."""

    _label_text = 'Layer Shape:'
    _tooltip_text = (
        'The size of the layer data array in each dimension, '
        'reported as (dim_0, dim_1, etc.).'
    )

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


class _SourceAttributeComponent(FileComponentBase):
    """Base for read-only source attribute display components.

    Subclasses set ``_source_attr`` to the name of the ``Source`` field
    and ``_label_text`` to the display label.  They are hidden
    automatically when the attribute is ``None``.

    For components that use a custom value widget (e.g. ``QLineEdit``),
    override ``_set_display_value`` to write to that widget instead.
    """

    _source_attr: str

    def _get_display_text(self, layer: Layer) -> str:
        value = getattr(layer.source, self._source_attr, None)
        return str(value) if value is not None else ''

    def _set_display_value(self, text: str) -> None:
        """Write *text* to the value widget.  Override for non-QLabel widgets."""
        self._display_label.setText(text)

    def clear(self) -> None:
        """Hide this component and reset display when no layer is selected."""
        self._display_label.setText('')
        self.set_visible(False)

    def _update_display(self, layer: Layer) -> None:
        value = getattr(layer.source, self._source_attr, None)
        self.set_visible(value is not None)
        if value is not None:
            self._set_display_value(str(value))


class SourcePath(_SourceAttributeComponent):
    """Read-only source path display using a ``QLineEdit``.

    Uses a ``QLineEdit`` for native single-line horizontal scrolling on
    long paths/URLs.  Hidden automatically when ``layer.source.path is None``.
    """

    _label_text = 'Source Path:'
    _source_attr = 'path'
    _under_label_in_vertical = True

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._path_line_edit = QLineEdit(parent=parent_widget)
        self._path_line_edit.setReadOnly(True)
        self._path_line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

    @property
    def value_widget(self) -> QWidget:
        return self._path_line_edit

    def _set_display_value(self, text: str) -> None:
        self._path_line_edit.setText(text)

    def clear(self) -> None:
        self.set_visible(False)
        self._path_line_edit.setText('')


class SourceReaderPlugin(_SourceAttributeComponent):
    """Read-only reader plugin name display, hidden when ``None``."""

    _label_text = 'Reader Plugin:'
    _source_attr = 'reader_plugin'


class SourceSample(_SourceAttributeComponent):
    """Read-only sample data id display, hidden when ``None``."""

    _label_text = 'Sample Data:'
    _source_attr = 'sample'


class SourceWidget(_SourceAttributeComponent):
    """Read-only source widget display, hidden when ``None``."""

    _label_text = 'Source Widget:'
    _source_attr = 'widget'


class SourceParent(_SourceAttributeComponent):
    """Read-only source parent layer display, hidden when ``None``."""

    _label_text = 'Source Parent:'
    _source_attr = 'parent'


class FileGeneralMetadata:
    """Coordinator that owns all file metadata component instances.

    Mirrors the ``AxisMetadata`` coordinator pattern — provides a
    ``components`` property for iteration by ``MetadataWidget``.

    The five source-attribute components (``SourcePath``,
    ``SourceReaderPlugin``, ``SourceSample``, ``SourceWidget``,
    ``SourceParent``) hide themselves automatically when the corresponding
    ``layer.source`` attribute is ``None``.
    """

    def __init__(self, parent_widget: QWidget) -> None:
        self._layer_name = LayerName(parent_widget)
        self._layer_shape = LayerShape(parent_widget)
        self._layer_dtype = LayerDataType(parent_widget)
        self._file_size = FileSize(parent_widget)
        self._source_path = SourcePath(parent_widget)
        self._source_reader_plugin = SourceReaderPlugin(parent_widget)
        self._source_sample = SourceSample(parent_widget)
        self._source_widget = SourceWidget(parent_widget)
        self._source_parent = SourceParent(parent_widget)

        self._components: list[FileComponentBase] = [
            self._layer_name,
            self._layer_shape,
            self._layer_dtype,
            self._file_size,
            self._source_path,
            self._source_reader_plugin,
            self._source_sample,
            self._source_widget,
            self._source_parent,
        ]
        self._selected_layer: Layer | None = None

    def connect_layer_events(self, layer: Layer) -> None:
        """Subscribe to *layer* events that require widget refresh."""
        self._selected_layer = layer
        layer.events.name.connect(self._on_name_changed)
        layer.events.data.connect(self._on_data_changed)

    def disconnect_layer_events(self, layer: Layer) -> None:
        """Unsubscribe from *layer* events."""
        self._selected_layer = None
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.name.disconnect(self._on_name_changed)
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.data.disconnect(self._on_data_changed)

    def _on_name_changed(self) -> None:
        if self._selected_layer is not None:
            for component in self._components:
                component.load_entries(self._selected_layer)

    def _on_data_changed(self) -> None:
        if self._selected_layer is not None:
            for component in (
                self._layer_shape,
                self._layer_dtype,
                self._file_size,
            ):
                component.load_entries(self._selected_layer)

    @property
    def components(self) -> list[FileComponentBase]:
        """All file components in display order."""
        return list(self._components)
