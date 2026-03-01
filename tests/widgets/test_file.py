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

from napari_metadata.widgets._file import (
    FileGeneralMetadata,
    FileSize,
    LayerDataType,
    LayerName,
    LayerShape,
    SourcePath,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from qtpy.QtWidgets import QWidget


class TestLayerShape:
    def test_displays_shape_for_image_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((10, 20)))
        component = LayerShape(viewer_model, parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == '(10, 20)'

    def test_displays_none_selected_when_no_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        component = LayerShape(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widget.text() == 'None selected'


class TestLayerDataType:
    def test_displays_dtype_for_image_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3), dtype=np.uint16))
        component = LayerDataType(viewer_model, parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == 'uint16'


class TestFileSize:
    def test_displays_size_for_image_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((100, 100), dtype=np.float64))
        component = FileSize(viewer_model, parent_widget)

        component.load_entries(layer)

        # The exact output depends on generate_display_size, but
        # it should contain bytes-related text and not be the placeholder.
        text = component.value_widget.text()
        assert text != 'None selected'
        assert len(text) > 0


class TestLayerName:
    def test_displays_layer_name(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)), name='test_image')
        component = LayerName(viewer_model, parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == 'test_image'

    def test_under_label_in_vertical_is_true(self):
        assert LayerName._under_label_in_vertical is True

    def test_editing_name_renames_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)), name='original')
        viewer_model.layers.selection.active = layer
        component = LayerName(viewer_model, parent_widget)
        component.load_entries(layer)

        component._line_edit.setText('renamed')
        component._line_edit.editingFinished.emit()

        assert layer.name == 'renamed'

    def test_editing_same_name_is_noop(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)), name='keep')
        viewer_model.layers.selection.active = layer
        component = LayerName(viewer_model, parent_widget)
        component.load_entries(layer)

        component._line_edit.setText('keep')
        component._line_edit.editingFinished.emit()

        assert layer.name == 'keep'

    def test_editing_with_no_active_layer_shows_message(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        component = LayerName(viewer_model, parent_widget)
        viewer_model.layers.selection.active = None

        component._line_edit.setText('anything')
        component._line_edit.editingFinished.emit()

        assert component._line_edit.text() == 'No layer selected'


class TestSourcePath:
    def test_under_label_in_vertical_is_true(self):
        assert SourcePath._under_label_in_vertical is True

    def test_displays_none_selected_when_no_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        component = SourcePath(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widget.text() == 'None selected'

    def test_line_edit_is_read_only(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        component = SourcePath(viewer_model, parent_widget)

        assert component._path_line_edit.isReadOnly()

    def test_displays_empty_string_for_layer_without_source(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        component = SourcePath(viewer_model, parent_widget)

        component.load_entries(layer)

        # Layers created programmatically have no source path
        assert component.value_widget.text() == ''


class TestFileGeneralMetadata:
    def test_has_five_components(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        meta = FileGeneralMetadata(viewer_model, parent_widget)

        assert len(meta.components) == 5

    def test_components_in_display_order(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        meta = FileGeneralMetadata(viewer_model, parent_widget)
        components = meta.components

        assert isinstance(components[0], LayerName)
        assert isinstance(components[1], LayerShape)
        assert isinstance(components[2], LayerDataType)
        assert isinstance(components[3], FileSize)
        assert isinstance(components[4], SourcePath)

    def test_components_property_returns_copy(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        meta = FileGeneralMetadata(viewer_model, parent_widget)
        components = meta.components
        components.clear()

        assert len(meta.components) == 5

    def test_all_components_load_entries(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3), dtype=np.uint8), name='test'
        )
        meta = FileGeneralMetadata(viewer_model, parent_widget)

        for component in meta.components:
            component.load_entries(layer)

        assert meta._layer_name.value_widget.text() == 'test'
        assert meta._layer_shape.value_widget.text() == '(4, 3)'
        assert meta._layer_dtype.value_widget.text() == 'uint8'
