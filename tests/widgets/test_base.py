"""Behavior tests for axis component base abstractions."""

import numpy as np
import pytest
from napari.components import ViewerModel
from qtpy.QtCore import QSignalBlocker
from qtpy.QtWidgets import QLineEdit, QWidget

from napari_metadata.layer_utils import (
    get_axes_labels,
    get_axes_translations,
    get_layer_dimensions,
    set_axes_translations,
)
from napari_metadata.widgets._base import AxisComponentBase, LayoutEntry


class _DummyAxisComponent(AxisComponentBase):
    _label_text = 'Dummy:'

    def __init__(self, viewer: ViewerModel, main_widget: QWidget) -> None:
        super().__init__(viewer, main_widget)
        self._value_line_edits: list[QLineEdit] = []
        self.create_count = 0
        self.refresh_count = 0
        self.last_applied: list[float] | None = None

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [*super()._all_widget_lists(), self._value_line_edits]

    def _create_widgets(self, layer):
        self.create_count += 1
        self._create_axis_name_labels(layer)
        for i in range(get_layer_dimensions(layer)):
            line_edit = QLineEdit(str(i))
            self._value_line_edits.append(line_edit)
        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer):
        self.refresh_count += 1
        labels = get_axes_labels(self._napari_viewer, layer)
        for i, label in enumerate(labels):
            if i < len(self._value_line_edits):
                with QSignalBlocker(self._value_line_edits[i]):
                    self._value_line_edits[i].setText(label)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._value_line_edits[axis_index]])]

    def _get_layer_values(self, layer) -> tuple:
        return get_axes_translations(self._napari_viewer, layer)

    def _apply_values(self, values: list) -> None:
        self.last_applied = list(values)
        set_axes_translations(self._napari_viewer, tuple(values))


@pytest.fixture
def viewer_model() -> ViewerModel:
    return ViewerModel()


@pytest.fixture
def parent_widget(qtbot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


class TestLayoutEntry:
    def test_defaults(self):
        entry = LayoutEntry(widgets=[])
        assert entry.row_span == 1
        assert entry.col_span == 1


class TestAxisComponentBaseLifecycle:
    def test_load_entries_creates_widgets_on_new_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        component = _DummyAxisComponent(viewer_model, parent_widget)

        component.load_entries(layer)

        assert component.create_count == 1
        assert component.refresh_count == 0
        assert component._selected_layer is layer
        assert component.num_axes == 2

    def test_load_entries_refreshes_for_same_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)), axis_labels=('y', 'x')
        )
        component = _DummyAxisComponent(viewer_model, parent_widget)

        component.load_entries(layer)
        first_widget_id = id(component._value_line_edits[0])

        layer.axis_labels = ('row', 'col')
        component.load_entries(layer)

        assert component.create_count == 1
        assert component.refresh_count == 1
        assert id(component._value_line_edits[0]) == first_widget_id
        assert component._value_line_edits[0].text() == 'row'
        assert component._value_line_edits[1].text() == 'col'

    def test_load_entries_clears_widgets_when_no_active_layer(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        component = _DummyAxisComponent(viewer_model, parent_widget)

        component.load_entries(layer)
        assert component.num_axes == 2

        viewer_model.layers.selection.active = None
        component.load_entries()

        assert component.num_axes == 0
        assert component._selected_layer is None

    def test_get_layout_entries_returns_name_value_checkbox_order(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        component = _DummyAxisComponent(viewer_model, parent_widget)
        component.load_entries(layer)

        entries = component.get_layout_entries(0)

        assert len(entries) == 3
        assert entries[0].widgets[0] is component._axis_name_labels[0]
        assert entries[1].widgets[0] is component._value_line_edits[0]
        assert entries[2].widgets[0] is component._inherit_checkboxes[0]


class TestAxisComponentBaseHelpers:
    def test_update_axis_name_labels_uses_label_or_index_fallback(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('a', 'b'),
        )
        component = _DummyAxisComponent(viewer_model, parent_widget)
        component.load_entries(layer)

        layer.axis_labels = ('new', '')
        component.update_axis_name_labels()

        assert component._axis_name_labels[0].text() == 'new'
        assert component._axis_name_labels[1].text() == '1'

    def test_set_checkboxes_visible_toggles_all(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        component = _DummyAxisComponent(viewer_model, parent_widget)
        component.load_entries(layer)

        component.set_checkboxes_visible(False)
        assert all(
            not checkbox.isVisible()
            for checkbox in component._inherit_checkboxes
        )

        component.set_checkboxes_visible(True)
        assert all(
            checkbox.isVisible() for checkbox in component._inherit_checkboxes
        )


class TestAxisComponentBaseInheritance:
    def test_inherit_layer_properties_merges_checked_axes(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        current = viewer_model.add_image(
            np.zeros((4, 3)), translate=(1.0, 2.0)
        )
        template = viewer_model.add_image(
            np.zeros((4, 3)), translate=(10.0, 20.0)
        )
        viewer_model.layers.selection.active = current

        component = _DummyAxisComponent(viewer_model, parent_widget)
        component.load_entries(current)
        component._inherit_checkboxes[0].setChecked(True)
        component._inherit_checkboxes[1].setChecked(False)

        component.inherit_layer_properties(template)

        assert tuple(current.translate) == pytest.approx((10.0, 2.0))
        assert component.last_applied == [10.0, 2.0]
        assert component._selected_layer is None

    def test_inherit_layer_properties_no_active_layer_is_noop(
        self, viewer_model: ViewerModel, parent_widget: QWidget
    ):
        template = viewer_model.add_image(
            np.zeros((4, 3)), translate=(10.0, 20.0)
        )
        viewer_model.layers.selection.active = None

        component = _DummyAxisComponent(viewer_model, parent_widget)
        component.inherit_layer_properties(template)

        assert component.last_applied is None
        assert component._selected_layer is None
