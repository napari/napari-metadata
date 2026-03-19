"""Behavior tests for the axis component refactor.

These tests focus on intended logic and maintainability-critical behavior:
axis-specific component behavior and coordinator semantics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import numpy as np
import pytest
from napari.layers import Image
from qtpy.QtWidgets import QComboBox

from napari_metadata.units import AxisUnitEnum
from napari_metadata.widgets._axis import (
    AxisLabels,
    AxisMetadata,
    AxisScales,
    AxisTranslations,
    AxisUnits,
)

if TYPE_CHECKING:
    from napari.layers import Layer
    from qtpy.QtWidgets import QWidget


def _make_layer(**kwargs: Any) -> Layer:
    return Image(np.zeros((4, 3)), **kwargs)


class TestAxisScales:
    def test_clamps_spinbox_display_and_layer_value(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(scale=(1.0, 1.0))
        scales = AxisScales(parent_widget)

        scales.load_entries(layer)
        spinbox = scales._spinboxes[0]
        spinbox.setValue(0.0)

        assert layer.scale[0] == pytest.approx(0.001)
        assert spinbox.value() == pytest.approx(0.001)

    def test_editing_finished_syncs_spinbox_to_clamped_layer_value(
        self, parent_widget: QWidget
    ):
        """After editing finishes, spinbox display syncs to the clamped layer value."""
        layer = _make_layer(scale=(1.0, 1.0))
        scales = AxisScales(parent_widget)
        scales.load_entries(layer)

        # Simulate typing a value below the clamp threshold
        spinbox = scales._spinboxes[0]
        spinbox.setValue(0.0005)
        spinbox.editingFinished.emit()

        # Layer clamps to 0.001; spinbox should sync back
        assert layer.scale[0] == pytest.approx(0.001)
        assert spinbox.value() == pytest.approx(0.001)

    def test_can_type_decimal_with_intermediate_zeros(
        self,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = _make_layer(scale=(1.0, 1.0))
        scales = AxisScales(parent_widget)

        scales.load_entries(layer)
        spinbox = scales._spinboxes[0]
        line_edit = spinbox.lineEdit()
        assert line_edit is not None

        line_edit.selectAll()
        qtbot.keyClicks(line_edit, '0.020')
        spinbox.editingFinished.emit()

        assert spinbox.value() == pytest.approx(0.02)
        assert layer.scale[0] == pytest.approx(0.02)


class TestAxisLabels:
    def test_refreshes_when_layer_axis_labels_change(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(axis_labels=('row', 'col'))
        labels = AxisLabels(parent_widget)

        labels.load_entries(layer)
        assert [lbl.text() for lbl in labels._axis_name_labels] == ['', '']
        assert [lbl.text() for lbl in labels._line_edits] == ['row', 'col']

        layer.axis_labels = ('new_row', 'new_col')
        labels.update_axis_name_labels(layer)

        # AxisLabels should refresh when axis labels change.
        assert [lbl.text() for lbl in labels._axis_name_labels] == ['', '']
        assert [lbl.text() for lbl in labels._line_edits] == [
            'new_row',
            'new_col',
        ]

    def test_get_line_edit_values_returns_current_text(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(axis_labels=('y', 'x'))
        labels = AxisLabels(parent_widget)
        labels.load_entries(layer)

        labels._line_edits[0].setText('row')
        labels._line_edits[1].setText('col')

        assert labels.get_line_edit_values() == ('row', 'col')


class TestAxisTranslations:
    def test_spinbox_value_change_writes_to_layer(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(translate=(0.0, 0.0))
        translations = AxisTranslations(parent_widget)
        translations.load_entries(layer)

        translations._spinboxes[0].setValue(5.0)

        assert tuple(layer.translate) == pytest.approx((5.0, 0.0))

    def test_refresh_updates_spinbox_from_layer(self, parent_widget: QWidget):
        layer = _make_layer(translate=(0.0, 0.0))
        translations = AxisTranslations(parent_widget)
        translations.load_entries(layer)

        layer.translate = (10.0, 20.0)
        translations.load_entries(layer)

        assert translations._spinboxes[0].value() == pytest.approx(10.0)
        assert translations._spinboxes[1].value() == pytest.approx(20.0)


class TestAxisMetadataCoordinator:
    def test_label_changes_propagate_to_sibling_components(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        axis_metadata = AxisMetadata(parent_widget)

        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        labels_component = axis_metadata._labels
        scales_component = axis_metadata._scales

        labels_component._line_edits[0].setText('test')
        labels_component._line_edits[0].editingFinished.emit()

        assert layer.axis_labels[0] == 'test'
        assert scales_component._axis_name_labels[0].text() == 'test'

    def test_set_checkboxes_visible_updates_all_components(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)

        axis_metadata.set_checkboxes_visible(False)
        for component in axis_metadata.components:
            assert all(
                checkbox.isHidden()
                for checkbox in component._inherit_checkboxes
            )

        axis_metadata.set_checkboxes_visible(True)
        for component in axis_metadata.components:
            assert all(
                not checkbox.isHidden()
                for checkbox in component._inherit_checkboxes
            )

    def test_components_property_returns_copy(self, parent_widget: QWidget):
        axis_metadata = AxisMetadata(parent_widget)
        components = axis_metadata.components
        components.clear()

        assert len(axis_metadata.components) == 4


class TestAxisUnits:
    def test_custom_units_flow_writes_line_edit_value(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(units=('pixel', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        type_combobox = units_component._type_comboboxes[0]
        type_combobox.setCurrentEnum(AxisUnitEnum.CUSTOM)
        units_component._unit_line_edits[0].setText('furlong')
        units_component._unit_line_edits[0].editingFinished.emit()

        assert str(layer.units[0]) == 'furlong'

    def test_custom_type_toggles_widget_visibility(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(units=('pixel', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        # Initially SPACE/TIME shows combobox and hides line edit.
        assert not units_component._unit_comboboxes[0].isHidden()
        assert units_component._unit_line_edits[0].isHidden()

        type_combobox = units_component._type_comboboxes[0]
        type_combobox.setCurrentEnum(AxisUnitEnum.CUSTOM)

        assert units_component._unit_comboboxes[0].isHidden()
        assert not units_component._unit_line_edits[0].isHidden()

    def test_invalid_pint_unit_warns_and_keeps_previous_value(
        self, parent_widget: QWidget
    ):
        """An unrecognised unit string should warn and leave the layer unchanged."""
        layer = _make_layer(units=('pixel', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        type_combobox = units_component._type_comboboxes[0]
        type_combobox.setCurrentEnum(AxisUnitEnum.CUSTOM)

        with patch('napari_metadata.widgets._axis.show_warning') as mock_warn:
            units_component._unit_line_edits[0].setText('notaunit_xyz')
            units_component._unit_line_edits[0].editingFinished.emit()

            mock_warn.assert_called_once()

        # Layer unit should be unchanged (kept at original value).
        assert str(layer.units[0]) == 'pixel'

    def test_populate_unit_combobox_selects_known_axis_type(
        self, parent_widget: QWidget
    ):
        combobox = QComboBox(parent=parent_widget)

        matched_type = AxisUnits._populate_unit_combobox('second', combobox)

        assert matched_type == AxisUnitEnum.TIME
        assert combobox.currentText() == 'second'
        assert combobox.count() == len(AxisUnitEnum.TIME.value.units)

    def test_populate_unit_combobox_leaves_custom_value_empty(
        self, parent_widget: QWidget
    ):
        combobox = QComboBox(parent=parent_widget)

        matched_type = AxisUnits._populate_unit_combobox('furlong', combobox)

        assert matched_type is None
        assert combobox.currentIndex() == -1
        assert combobox.count() == 0

    def test_refresh_values_updates_known_and_custom_units(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(units=('pixel', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        layer.units = ('furlong', 'hour')
        units_component.load_entries(layer)

        assert (
            units_component._type_comboboxes[0].currentEnum()
            == AxisUnitEnum.CUSTOM
        )
        assert units_component._unit_line_edits[0].text() == 'furlong'
        assert units_component._unit_comboboxes[0].count() == 0
        assert (
            units_component._type_comboboxes[1].currentEnum()
            == AxisUnitEnum.TIME
        )
        assert units_component._unit_comboboxes[1].currentText() == 'hour'

    def test_custom_none_text_resets_layer_unit_to_pixel(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(units=('pixel', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        units_component._type_comboboxes[0].setCurrentEnum(AxisUnitEnum.CUSTOM)
        units_component._unit_line_edits[0].setText('None')
        units_component._unit_line_edits[0].editingFinished.emit()

        assert str(layer.units[0]) == 'pixel'
        assert units_component._unit_line_edits[0].text() == 'pixel'

    def test_switching_custom_axis_type_uses_category_default(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(units=('furlong', 'second'))
        units_component = AxisUnits(parent_widget)
        units_component.load_entries(layer)

        units_component._type_comboboxes[0].setCurrentEnum(AxisUnitEnum.SPACE)

        assert str(layer.units[0]) == AxisUnitEnum.SPACE.value.default
        assert units_component._unit_comboboxes[0].currentText() == 'pixel'


class TestAxisEventDriven:
    """Tests that programmatic layer changes update the axis metadata widgets."""

    def test_axis_labels_event_updates_line_edits(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(axis_labels=('y', 'x'))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        layer.axis_labels = ('row', 'col')

        labels = axis_metadata._labels
        assert [le.text() for le in labels._line_edits] == ['row', 'col']

    def test_axis_labels_event_updates_sibling_axis_name_labels(
        self, parent_widget: QWidget
    ):
        layer = _make_layer(axis_labels=('y', 'x'), scale=(1.0, 1.0))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        layer.axis_labels = ('A', 'B')

        scales = axis_metadata._scales
        assert [lbl.text() for lbl in scales._axis_name_labels] == ['A', 'B']

    def test_scale_event_updates_spinboxes(self, parent_widget: QWidget):
        layer = _make_layer(scale=(1.0, 2.0))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        layer.scale = (3.0, 4.0)

        scales = axis_metadata._scales
        assert scales._spinboxes[0].value() == pytest.approx(3.0)
        assert scales._spinboxes[1].value() == pytest.approx(4.0)

    def test_translate_event_updates_spinboxes(self, parent_widget: QWidget):
        layer = _make_layer(translate=(0.0, 0.0))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        layer.translate = (10.0, 20.0)

        translations = axis_metadata._translations
        assert translations._spinboxes[0].value() == pytest.approx(10.0)
        assert translations._spinboxes[1].value() == pytest.approx(20.0)

    def test_units_event_updates_comboboxes(self, parent_widget: QWidget):
        layer = _make_layer(units=('pixel', 'pixel'))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)

        layer.units = ('millimeter', 'second')

        units_cmp = axis_metadata._units
        assert units_cmp._unit_comboboxes[0].currentText() == str(
            layer.units[0]
        )
        assert units_cmp._unit_comboboxes[1].currentText() == str(
            layer.units[1]
        )

    def test_disconnect_stops_updates(self, parent_widget: QWidget):
        layer = _make_layer(scale=(1.0, 1.0))
        axis_metadata = AxisMetadata(parent_widget)
        for component in axis_metadata.components:
            component.load_entries(layer)
        axis_metadata.connect_layer_events(layer)
        axis_metadata.disconnect_layer_events(layer)

        layer.scale = (5.0, 6.0)

        scales = axis_metadata._scales
        assert scales._spinboxes[0].value() == pytest.approx(1.0)
        assert scales._spinboxes[1].value() == pytest.approx(1.0)


class TestAxisComponentsWithoutLayer:
    """Guard paths invoked when no layer has been loaded into a component."""

    def test_axis_labels_get_value_entries_returns_line_edit_entry(
        self, parent_widget: QWidget
    ):
        """_get_value_entries returns an entry wrapping the correct QLineEdit."""
        layer = _make_layer(axis_labels=('y', 'x'))
        labels = AxisLabels(parent_widget)
        labels.load_entries(layer)

        entries = labels._get_value_entries(0)

        assert len(entries) == 1
        assert entries[0].widgets[0] is labels._line_edits[0]

    def test_axis_labels_editing_finished_noop_without_layer(
        self, parent_widget: QWidget
    ):
        labels = AxisLabels(parent_widget)
        assert labels._selected_layer is None
        assert labels.num_axes == 0
        labels._on_editing_finished()  # no layer — must not raise

    def test_axis_translations_on_value_changed_noop_without_layer(
        self, parent_widget: QWidget
    ):
        translations = AxisTranslations(parent_widget)
        assert translations._selected_layer is None
        assert translations.num_axes == 0
        translations._on_value_changed()  # no layer — must not raise

    def test_axis_scales_on_value_changed_noop_without_layer(
        self, parent_widget: QWidget
    ):
        scales = AxisScales(parent_widget)
        assert scales._selected_layer is None
        assert scales.num_axes == 0
        scales._on_value_changed()  # no layer — must not raise

    def test_axis_scales_editing_finished_noop_without_layer(
        self, parent_widget: QWidget
    ):
        scales = AxisScales(parent_widget)
        assert scales._selected_layer is None
        scales._on_editing_finished()  # no layer — must not raise

    def test_axis_units_sync_line_edits_noop_without_layer(
        self, parent_widget: QWidget
    ):
        units = AxisUnits(parent_widget)
        assert units._selected_layer is None
        assert units.num_axes == 0
        units._sync_line_edit_texts()  # no layer — must not raise

    def test_axis_units_write_units_noop_without_layer(
        self, parent_widget: QWidget
    ):
        units = AxisUnits(parent_widget)
        assert units._selected_layer is None
        units._write_units_to_layer()  # no layer — must not raise

    def test_axis_units_on_type_changed_noop_without_layer(
        self, parent_widget: QWidget
    ):
        units = AxisUnits(parent_widget)
        assert units._selected_layer is None
        units._on_type_changed()  # no layer — must not raise

    def test_axis_metadata_on_labels_changed_noop_without_layer(
        self, parent_widget: QWidget
    ):
        metadata = AxisMetadata(parent_widget)
        assert metadata._selected_layer is None
        metadata._on_labels_changed()  # must not raise
