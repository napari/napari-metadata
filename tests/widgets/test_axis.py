"""Behavior tests for the axis component refactor.

These tests focus on intended logic and maintainability-critical behavior:
axis-specific component behavior and coordinator semantics.
"""

import numpy as np
import pytest
from napari.components import ViewerModel
from qtpy.QtWidgets import QWidget

from napari_metadata.units import AxisUnitEnum
from napari_metadata.widgets._axis import (
    AxisLabels,
    AxisMetadata,
    AxisScales,
    AxisUnits,
)


@pytest.fixture
def viewer_model() -> ViewerModel:
    return ViewerModel()


@pytest.fixture
def parent_widget(qtbot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


class TestAxisScales:
    def test_clamps_spinbox_display_and_layer_value(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        scales = AxisScales(viewer_model, parent_widget)

        scales.load_entries(layer)
        spinbox = scales._spinboxes[0]
        spinbox.setValue(0.0)

        assert layer.scale[0] == pytest.approx(0.001)
        assert spinbox.value() == pytest.approx(0.001)


class TestAxisLabels:
    def test_shows_index_labels_and_update_is_noop(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('row', 'col'),
        )
        labels = AxisLabels(viewer_model, parent_widget)

        labels.load_entries(layer)
        assert [lbl.text() for lbl in labels._axis_name_labels] == ['0', '1']

        layer.axis_labels = ('new_row', 'new_col')
        labels.update_axis_name_labels()

        # AxisLabels intentionally keeps index labels.
        assert [lbl.text() for lbl in labels._axis_name_labels] == ['0', '1']


class TestAxisMetadataCoordinator:
    def test_label_changes_propagate_to_sibling_components(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        axis_metadata = AxisMetadata(viewer_model, parent_widget)

        for component in axis_metadata.components:
            component.load_entries(layer)

        labels_component = axis_metadata._labels
        scales_component = axis_metadata._scales

        labels_component._line_edits[0].setText('test')
        labels_component._line_edits[0].editingFinished.emit()

        assert layer.axis_labels[0] == 'test'
        assert scales_component._axis_name_labels[0].text() == 'test'

    def test_set_checkboxes_visible_updates_all_components(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        axis_metadata = AxisMetadata(viewer_model, parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)

        axis_metadata.set_checkboxes_visible(False)
        for component in axis_metadata.components:
            assert all(
                not checkbox.isVisible()
                for checkbox in component._inherit_checkboxes
            )

        axis_metadata.set_checkboxes_visible(True)
        for component in axis_metadata.components:
            assert all(
                checkbox.isVisible()
                for checkbox in component._inherit_checkboxes
            )

    def test_components_property_returns_copy(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        axis_metadata = AxisMetadata(viewer_model, parent_widget)
        components = axis_metadata.components
        components.clear()

        assert len(axis_metadata.components) == 4


class TestAxisUnits:
    def test_string_units_flow_writes_line_edit_value(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            units=('pixel', 'second'),
        )
        units_component = AxisUnits(viewer_model, parent_widget)
        units_component.load_entries(layer)

        type_combobox = units_component._type_comboboxes[0]
        string_index = type_combobox.findData(AxisUnitEnum.STRING)
        assert string_index != -1

        type_combobox.setCurrentIndex(string_index)
        units_component._unit_line_edits[0].setText('furlong')
        units_component._unit_line_edits[0].editingFinished.emit()

        assert str(layer.units[0]) == 'furlong'

    def test_string_type_toggles_widget_visibility(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            units=('pixel', 'second'),
        )
        units_component = AxisUnits(viewer_model, parent_widget)
        units_component.load_entries(layer)

        # Initially SPACE/TIME shows combobox and hides line edit.
        assert units_component._unit_comboboxes[0].isVisible()
        assert not units_component._unit_line_edits[0].isVisible()

        type_combobox = units_component._type_comboboxes[0]
        string_index = type_combobox.findData(AxisUnitEnum.STRING)
        type_combobox.setCurrentIndex(string_index)

        assert not units_component._unit_comboboxes[0].isVisible()
        assert units_component._unit_line_edits[0].isVisible()
