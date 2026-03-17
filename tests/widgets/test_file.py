"""Behavior tests for file component base class and concrete file components.

These tests verify:
* ``FileComponentBase`` lifecycle (load_entries, _update_display)
* ``ComponentBase`` shared initialization
* Concrete component display text
* ``LayerName`` bidirectional editing
* ``SourcePath`` read-only behavior
* ``FileGeneralMetadata`` coordinator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari.layers import Image

from napari_metadata.widgets._file import (
    FileGeneralMetadata,
    FileSize,
    LayerDataType,
    LayerName,
    LayerShape,
    SourceParent,
    SourcePath,
    SourceReaderPlugin,
    SourceSample,
    SourceWidget,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from qtpy.QtWidgets import QWidget


class TestLayerShape:
    def test_displays_shape_for_image_layer(self, parent_widget: QWidget):
        layer = Image(np.zeros((10, 20)))
        component = LayerShape(parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == '(10, 20)'

    def test_displays_none_selected_when_cleared(self, parent_widget: QWidget):
        component = LayerShape(parent_widget)

        component.clear()

        assert component.value_widget.text() == ''


class TestLayerDataType:
    def test_displays_dtype_for_image_layer(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3), dtype=np.uint16))
        component = LayerDataType(parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == 'uint16'


class TestFileSize:
    def test_displays_size_for_image_layer(self, parent_widget: QWidget):
        layer = Image(np.zeros((100, 100), dtype=np.float64))
        component = FileSize(parent_widget)

        component.load_entries(layer)

        # The exact output depends on generate_display_size, but
        # it should contain bytes-related text and not be the placeholder.
        text = component.value_widget.text()
        assert text != 'None selected'
        assert len(text) > 0


class TestLayerName:
    def test_displays_layer_name(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)), name='test_image')
        component = LayerName(parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == 'test_image'

    def test_under_label_in_vertical_is_true(self):
        assert LayerName._under_label_in_vertical is True

    def test_editing_name_renames_layer(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)), name='original')
        component = LayerName(parent_widget)
        component.load_entries(layer)

        component._line_edit.setText('renamed')
        component._line_edit.editingFinished.emit()

        assert layer.name == 'renamed'

    def test_editing_same_name_is_noop(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)), name='keep')
        component = LayerName(parent_widget)
        component.load_entries(layer)

        component._line_edit.setText('keep')
        component._line_edit.editingFinished.emit()

        assert layer.name == 'keep'

    def test_editing_with_no_active_layer_shows_message(
        self, parent_widget: QWidget
    ):
        component = LayerName(parent_widget)

        component._line_edit.setText('anything')
        component._line_edit.editingFinished.emit()

        assert component._line_edit.text() == 'No layer selected'


class TestSourcePath:
    def test_under_label_in_vertical_is_true(self):
        assert SourcePath._under_label_in_vertical is True

    def test_displays_none_selected_when_cleared(self, parent_widget: QWidget):
        component = SourcePath(parent_widget)

        component.clear()

        assert component.value_widget.text() == ''

    def test_line_edit_is_read_only(self, parent_widget: QWidget):
        component = SourcePath(parent_widget)

        assert component._path_line_edit.isReadOnly()

    def test_displays_empty_string_for_layer_without_source(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = SourcePath(parent_widget)

        component.load_entries(layer)

        # Layers created programmatically have no source path
        assert component.value_widget.text() == ''


class TestSourceReaderPlugin:
    def test_hidden_when_cleared(self, parent_widget: QWidget):
        component = SourceReaderPlugin(parent_widget)

        component.clear()

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_hidden_when_layer_has_no_reader_plugin(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = SourceReaderPlugin(parent_widget)

        component.load_entries(layer)

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_source_reader_plugin_component_exists(
        self, parent_widget: QWidget
    ):
        """Verify SourceReaderPlugin component is initialized with correct attributes."""
        component = SourceReaderPlugin(parent_widget)
        assert component._label_text == 'Reader Plugin:'
        assert component._source_attr == 'reader_plugin'


class TestSourceSample:
    def test_hidden_when_cleared(self, parent_widget: QWidget):
        component = SourceSample(parent_widget)

        component.clear()

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_hidden_when_layer_has_no_sample(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)))
        component = SourceSample(parent_widget)

        component.load_entries(layer)

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_source_sample_component_exists(self, parent_widget: QWidget):
        """Verify SourceSample component is initialized with correct attributes."""
        component = SourceSample(parent_widget)
        assert component._label_text == 'Sample Data:'
        assert component._source_attr == 'sample'


class TestSourceWidget:
    def test_hidden_when_cleared(self, parent_widget: QWidget):
        component = SourceWidget(parent_widget)

        component.clear()

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_hidden_when_layer_has_no_widget(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)))
        component = SourceWidget(parent_widget)

        component.load_entries(layer)

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_source_widget_component_exists(self, parent_widget: QWidget):
        """Verify SourceWidget component is initialized and has correct label."""
        from napari_metadata.widgets._file import SourceWidget

        component = SourceWidget(parent_widget)
        assert component._label_text == 'Source Widget:'
        assert component._source_attr == 'widget'


class TestSourceParent:
    def test_hidden_when_cleared(self, parent_widget: QWidget):
        component = SourceParent(parent_widget)

        component.clear()

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_hidden_when_layer_has_no_parent(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)))
        component = SourceParent(parent_widget)

        component.load_entries(layer)

        assert not component.component_label.isVisible()
        assert not component.value_widget.isVisible()

    def test_source_parent_component_exists(self, parent_widget: QWidget):
        """Verify SourceParent component is initialized with correct attributes."""
        component = SourceParent(parent_widget)
        assert component._label_text == 'Source Parent:'
        assert component._source_attr == 'parent'


class TestFileGeneralMetadata:
    def test_has_five_components(self, parent_widget: QWidget):
        meta = FileGeneralMetadata(parent_widget)

        assert len(meta.components) == 9

    def test_components_in_display_order(self, parent_widget: QWidget):
        meta = FileGeneralMetadata(parent_widget)
        components = meta.components

        assert isinstance(components[0], LayerName)
        assert isinstance(components[1], LayerShape)
        assert isinstance(components[2], LayerDataType)
        assert isinstance(components[3], FileSize)
        assert isinstance(components[4], SourcePath)
        assert isinstance(components[5], SourceReaderPlugin)
        assert isinstance(components[6], SourceSample)
        assert isinstance(components[7], SourceWidget)
        assert isinstance(components[8], SourceParent)

    def test_components_property_returns_copy(self, parent_widget: QWidget):
        meta = FileGeneralMetadata(parent_widget)
        components = meta.components
        components.clear()

        assert len(meta.components) == 9

    def test_all_components_load_entries(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3), dtype=np.uint8), name='test')
        meta = FileGeneralMetadata(parent_widget)

        for component in meta.components:
            component.load_entries(layer)

        assert meta._layer_name.value_widget.text() == 'test'
        assert meta._layer_shape.value_widget.text() == '(4, 3)'
        assert meta._layer_dtype.value_widget.text() == 'uint8'

    def test_source_components_with_all_attributes(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        """Test FileGeneralMetadata with a layer having multiple source attributes."""
        from napari.layers._source import Source

        parent_layer = viewer_model.add_image(np.zeros((4, 3)), name='parent')
        layer = viewer_model.add_image(np.zeros((4, 3)), name='child')
        layer._source = Source(
            reader_plugin='tiff-reader',
            sample=('plugin', 'sample_id'),
            parent=parent_layer,
        )
        meta = FileGeneralMetadata(parent_widget)

        for component in meta.components:
            component.load_entries(layer)

        # Verify all components have been initialized and are accessible
        assert meta._source_path is not None
        assert meta._source_reader_plugin is not None
        assert meta._source_sample is not None
        assert meta._source_widget is not None
        assert meta._source_parent is not None

        # The components should be accessible; widget will be hidden since it's None
        assert isinstance(meta._source_reader_plugin.value_widget.text(), str)
        assert isinstance(meta._source_sample.value_widget.text(), str)
        assert isinstance(meta._source_parent.value_widget.text(), str)


class TestFileEventDriven:
    """Tests that programmatic layer changes update the file metadata widgets."""

    def test_name_event_updates_layer_name_widget(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)), name='original')
        file_meta = FileGeneralMetadata(parent_widget)
        for component in file_meta.components:
            component.load_entries(layer)
        file_meta.connect_layer_events(layer)

        layer.name = 'renamed'

        assert file_meta._layer_name.value_widget.text() == 'renamed'

    def test_data_event_updates_shape_widget(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3), dtype=np.uint8), name='test')
        file_meta = FileGeneralMetadata(parent_widget)
        for component in file_meta.components:
            component.load_entries(layer)
        file_meta.connect_layer_events(layer)

        layer.data = np.zeros((6, 5), dtype=np.uint8)

        assert file_meta._layer_shape.value_widget.text() == '(6, 5)'

    def test_data_event_updates_dtype_widget(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3), dtype=np.uint8))
        file_meta = FileGeneralMetadata(parent_widget)
        for component in file_meta.components:
            component.load_entries(layer)
        file_meta.connect_layer_events(layer)

        layer.data = np.zeros((4, 3), dtype=np.float32)

        assert file_meta._layer_dtype.value_widget.text() == 'float32'

    def test_source_path_not_updated_on_data_change(
        self, parent_widget: QWidget
    ):
        """SourcePath is excluded from data-change refresh (immutable after creation)."""
        layer = Image(np.zeros((4, 3)), name='test')
        file_meta = FileGeneralMetadata(parent_widget)
        for component in file_meta.components:
            component.load_entries(layer)
        file_meta.connect_layer_events(layer)
        initial_path = file_meta._source_path.value_widget.text()

        layer.data = np.zeros((6, 5))

        assert file_meta._source_path.value_widget.text() == initial_path

    def test_disconnect_stops_name_updates(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)), name='first')
        file_meta = FileGeneralMetadata(parent_widget)
        for component in file_meta.components:
            component.load_entries(layer)
        file_meta.connect_layer_events(layer)
        file_meta.disconnect_layer_events(layer)

        layer.name = 'second'

        assert file_meta._layer_name.value_widget.text() == 'first'
