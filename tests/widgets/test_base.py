"""Behavior tests for axis component base abstractions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from napari.layers import Image
from qtpy.QtCore import QSignalBlocker
from qtpy.QtWidgets import QLineEdit

from napari_metadata.widgets._base import (
    AxisComponentBase,
    BoundFileComponentBase,
    BoundLayerCoordinator,
    BoundLayerOwner,
    ComponentBase,
    FileComponentBase,
    LayoutEntry,
)

if TYPE_CHECKING:
    from napari.layers import Layer
    from qtpy.QtWidgets import QWidget


class TestComponentBase:
    def test_cannot_instantiate_directly(self, parent_widget: QWidget):
        with pytest.raises(TypeError):
            ComponentBase(parent_widget)

    def test_shared_init_sets_parent(self, parent_widget: QWidget):
        component = _DummyFileComponent(parent_widget)

        assert component._parent_widget is parent_widget

    def test_shared_init_creates_bold_label_with_tooltip(
        self, parent_widget: QWidget
    ):
        component = _DummyFileComponent(parent_widget)

        label = component.component_label
        assert label.text() == 'Test:'
        assert 'bold' in label.styleSheet()
        assert label.toolTip() == 'File tooltip.'


class _DummyBoundLayerOwner(BoundLayerOwner):
    def bind(self, layer: Layer) -> None:
        self._bind_layer_reference(layer)

    def unbind(self) -> None:
        self._unbind_layer_reference()


class _DummyBindable:
    def __init__(self) -> None:
        self.bound_layers: list[Layer] = []
        self.unbind_count = 0

    def bind_layer(self, layer: Layer) -> None:
        self.bound_layers.append(layer)

    def unbind_layer(self) -> None:
        self.unbind_count += 1


class _DummyCoordinator(BoundLayerCoordinator):
    def __init__(self) -> None:
        super().__init__()
        self._bindable = _DummyBindable()
        self.connected_layers: list[Layer] = []
        self.disconnected_layers: list[Layer] = []

    @property
    def components(self) -> list[_DummyBindable]:
        return [self._bindable]

    def _connect_bound_layer_events(self, layer: Layer) -> None:
        self.connected_layers.append(layer)

    def _disconnect_bound_layer_events(self, layer: Layer) -> None:
        self.disconnected_layers.append(layer)


class _DummyBoundFileComponent(BoundFileComponentBase):
    _label_text = 'Bound:'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._line_edit = QLineEdit(parent=parent_widget)
        self.connected_count = 0
        self.disconnected_count = 0

    @property
    def value_widget(self) -> QLineEdit:
        return self._line_edit

    def _get_display_text(self, layer: Layer) -> str:
        return layer.name

    def _update_display(self, layer: Layer) -> None:
        self._line_edit.setText(self._get_display_text(layer))

    def _clear_bound_display(self) -> None:
        self._line_edit.setText('')

    def _connect_bound_layer_signals(self) -> None:
        self.connected_count += 1

    def _disconnect_bound_layer_signals(self) -> None:
        self.disconnected_count += 1


class TestBoundLayerOwner:
    def test_require_selected_layer_raises_when_unbound(self):
        owner = _DummyBoundLayerOwner()

        with pytest.raises(RuntimeError, match='not bound to a layer'):
            owner._require_selected_layer()

    def test_bind_and_unbind_layer_reference(self):
        owner = _DummyBoundLayerOwner()
        layer = Image(np.zeros((4, 3)))

        owner.bind(layer)
        assert owner._require_selected_layer() is layer

        owner.unbind()
        with pytest.raises(RuntimeError, match='not bound to a layer'):
            owner._require_selected_layer()


class TestBoundLayerCoordinator:
    def test_bind_layer_binds_children_and_connects_events(self):
        coordinator = _DummyCoordinator()
        layer = Image(np.zeros((4, 3)))

        coordinator.bind_layer(layer)

        assert coordinator._require_selected_layer() is layer
        assert coordinator._bindable.bound_layers == [layer]
        assert coordinator.connected_layers == [layer]

    def test_unbind_layer_disconnects_events_and_children(self):
        coordinator = _DummyCoordinator()
        layer = Image(np.zeros((4, 3)))
        coordinator.bind_layer(layer)

        coordinator.unbind_layer()

        assert coordinator.disconnected_layers == [layer]
        assert coordinator._bindable.unbind_count == 1
        with pytest.raises(RuntimeError, match='not bound to a layer'):
            coordinator._require_selected_layer()

    def test_rebinding_same_layer_is_noop(self):
        coordinator = _DummyCoordinator()
        layer = Image(np.zeros((4, 3)))
        coordinator.bind_layer(layer)

        coordinator.bind_layer(layer)  # same layer: should be a no-op

        assert coordinator._bindable.bound_layers == [layer]  # bound only once
        assert coordinator.connected_layers == [layer]  # connected only once

    def test_binding_different_layer_unbinds_old_first(self):
        coordinator = _DummyCoordinator()
        layer_a = Image(np.zeros((4, 3)))
        layer_b = Image(np.zeros((4, 3)))
        coordinator.bind_layer(layer_a)

        coordinator.bind_layer(layer_b)

        assert coordinator.disconnected_layers == [layer_a]
        assert coordinator._bindable.unbind_count == 1
        assert coordinator._require_selected_layer() is layer_b
        assert coordinator.connected_layers == [layer_a, layer_b]


class TestBoundFileComponentBase:
    def test_bind_layer_updates_display_and_connects_signals(
        self, parent_widget: QWidget
    ):
        component = _DummyBoundFileComponent(parent_widget)
        layer = Image(np.zeros((4, 3)), name='bound')

        component.bind_layer(layer)

        assert component._require_selected_layer() is layer
        assert component.value_widget.text() == 'bound'
        assert component.connected_count == 1

    def test_unbind_layer_clears_display_and_disconnects_signals(
        self, parent_widget: QWidget
    ):
        component = _DummyBoundFileComponent(parent_widget)
        layer = Image(np.zeros((4, 3)), name='bound')
        component.bind_layer(layer)

        component.unbind_layer()

        assert component.value_widget.text() == ''
        assert component.disconnected_count == 1
        with pytest.raises(RuntimeError, match='not bound to a layer'):
            component._require_selected_layer()

    def test_rebinding_same_layer_refreshes_display_without_reconnecting(
        self, parent_widget: QWidget
    ):
        component = _DummyBoundFileComponent(parent_widget)
        layer = Image(np.zeros((4, 3)), name='first')
        component.bind_layer(layer)

        layer.name = 'updated'
        component.bind_layer(layer)  # same layer object

        assert component.value_widget.text() == 'updated'
        assert component.connected_count == 1  # no reconnect


class _DummyAxisComponent(AxisComponentBase):
    _label_text = 'Dummy:'
    _tooltip_text = 'Axis tooltip.'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._value_line_edits: list[QLineEdit] = []
        self.create_count = 0
        self.refresh_count = 0
        self.last_applied: list[float] | None = None

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [*super()._all_widget_lists(), self._value_line_edits]

    def _create_widgets(self, layer: Layer) -> None:
        self.create_count += 1
        self._create_axis_name_labels(layer)
        for i in range(layer.ndim):
            line_edit = QLineEdit(str(i))
            self._value_line_edits.append(line_edit)
        self._create_inherit_checkboxes(layer)

    def _refresh_values(self, layer: Layer) -> None:
        self.refresh_count += 1
        labels = layer.axis_labels
        for i, label in enumerate(labels):
            if i < len(self._value_line_edits):
                with QSignalBlocker(self._value_line_edits[i]):
                    self._value_line_edits[i].setText(label)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._value_line_edits[axis_index]])]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return tuple(layer.translate)

    def _apply_values(self, layer: Layer, values: list) -> None:
        self.last_applied = list(values)
        layer.translate = tuple(values)


class _DummyAxisComponentWithExplicitTooltips(_DummyAxisComponent):
    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        line_edit = self._value_line_edits[axis_index]
        return [
            LayoutEntry(
                widgets=[line_edit],
                tooltips=[f'Explicit tooltip {axis_index}.'],
            )
        ]


class TestLayoutEntry:
    def test_defaults(self):
        entry = LayoutEntry(widgets=[])
        assert entry.row_span == 1
        assert entry.col_span == 1


class TestAxisComponentBaseLifecycle:
    def test_load_entries_creates_widgets_on_new_layer(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = _DummyAxisComponent(parent_widget)

        component.load_entries(layer)

        assert component.create_count == 1
        assert component.refresh_count == 0
        assert component._selected_layer is layer
        assert component.num_axes == 2

    def test_load_entries_refreshes_for_same_layer(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)), axis_labels=('y', 'x'))
        component = _DummyAxisComponent(parent_widget)

        component.load_entries(layer)
        first_widget_id = id(component._value_line_edits[0])

        layer.axis_labels = ('row', 'col')
        component.load_entries(layer)

        assert component.create_count == 1
        assert component.refresh_count == 1
        assert id(component._value_line_edits[0]) == first_widget_id
        assert component._value_line_edits[0].text() == 'row'
        assert component._value_line_edits[1].text() == 'col'

    def test_clear_removes_all_widgets(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)))
        component = _DummyAxisComponent(parent_widget)

        component.load_entries(layer)
        assert component.num_axes == 2

        component.clear()

        assert component.num_axes == 0
        assert component._selected_layer is None

    def test_get_layout_entries_structure_and_tooltips(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = _DummyAxisComponent(parent_widget)
        component.load_entries(layer)

        for axis_idx in range(layer.data.ndim):
            entries = component.get_layout_entries(axis_idx)

            assert len(entries) == 3
            assert (
                entries[0].widgets[0] is component._axis_name_labels[axis_idx]
            )
            assert (
                entries[1].widgets[0] is component._value_line_edits[axis_idx]
            )
            assert (
                entries[2].widgets[0]
                is component._inherit_checkboxes[axis_idx]
            )
            # tooltip applied only to value entry widgets, not name/checkbox
            assert entries[0].widgets[0].toolTip() == ''
            for widget in entries[1].widgets:
                assert widget.toolTip() == 'Axis tooltip.'
            assert entries[2].widgets[0].toolTip() == ''

    def test_get_layout_entries_uses_explicit_entry_tooltips(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = _DummyAxisComponentWithExplicitTooltips(parent_widget)
        component.load_entries(layer)

        entries = component.get_layout_entries(1)

        assert entries[1].widgets[0].toolTip() == 'Explicit tooltip 1.'

    def test_get_layout_entries_raises_on_tooltip_widget_count_mismatch(
        self, parent_widget: QWidget
    ):
        class _InvalidTooltipComponent(_DummyAxisComponent):
            def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
                return [
                    LayoutEntry(
                        widgets=[self._value_line_edits[axis_index]],
                        tooltips=['one', 'two'],
                    )
                ]

        layer = Image(np.zeros((4, 3)))
        component = _InvalidTooltipComponent(parent_widget)
        component.load_entries(layer)

        with pytest.raises(
            ValueError,
            match='LayoutEntry.tooltips must match the number of widgets.',
        ):
            component.get_layout_entries(0)


class TestAxisComponentBaseHelpers:
    def test_update_axis_name_labels_uses_label_or_index_fallback(
        self, parent_widget: QWidget
    ):
        layer = Image(
            np.zeros((4, 3)),
            axis_labels=('a', 'b'),
        )
        component = _DummyAxisComponent(parent_widget)
        component.load_entries(layer)

        layer.axis_labels = ('new', '')
        component.update_axis_name_labels(layer)

        assert component._axis_name_labels[0].text() == 'new'
        assert component._axis_name_labels[1].text() == '1'

    def test_set_checkboxes_visible_toggles_all(self, parent_widget: QWidget):
        layer = Image(np.zeros((4, 3)))
        component = _DummyAxisComponent(parent_widget)
        component.load_entries(layer)

        component.set_checkboxes_visible(False)
        assert all(
            checkbox.isHidden() for checkbox in component._inherit_checkboxes
        )

        component.set_checkboxes_visible(True)
        assert all(
            not checkbox.isHidden()
            for checkbox in component._inherit_checkboxes
        )


class TestAxisComponentBaseInheritance:
    def test_inherit_layer_properties_merges_checked_axes(
        self, parent_widget: QWidget
    ):
        current = Image(np.zeros((4, 3)), translate=(1.0, 2.0))
        template = Image(np.zeros((4, 3)), translate=(10.0, 20.0))

        component = _DummyAxisComponent(parent_widget)
        component.load_entries(current)
        component._inherit_checkboxes[0].setChecked(True)
        component._inherit_checkboxes[1].setChecked(False)

        component.inherit_layer_properties(template, current)

        assert tuple(current.translate) == pytest.approx((10.0, 2.0))
        assert component.last_applied == [10.0, 2.0]
        assert component._selected_layer is current

    def test_inherit_layer_properties_uses_both_layers(
        self, parent_widget: QWidget
    ):
        """Checked axes get template values, unchecked keep current."""
        current = Image(np.zeros((4, 3)), translate=(1.0, 2.0))
        template = Image(np.zeros((4, 3)), translate=(10.0, 20.0))

        component = _DummyAxisComponent(parent_widget)
        component.load_entries(current)
        component._inherit_checkboxes[0].setChecked(False)
        component._inherit_checkboxes[1].setChecked(True)

        component.inherit_layer_properties(template, current)

        assert tuple(current.translate) == pytest.approx((1.0, 20.0))


class _DummyFileComponent(FileComponentBase):
    _label_text = 'Test:'
    _tooltip_text = 'File tooltip.'
    _under_label_in_vertical = True

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self.get_text_calls: list[str] = []

    def _get_display_text(self, layer: Layer) -> str:
        text = f'shape={layer.data.shape}'
        self.get_text_calls.append(text)
        return text


class _DummyFileComponentWithLineEdit(FileComponentBase):
    """File component with a QLineEdit value_widget, used for custom widget tests."""

    _label_text = 'Custom:'
    _tooltip_text = 'Line edit tooltip.'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._line_edit = QLineEdit(parent=parent_widget)

    @property
    def value_widget(self) -> QLineEdit:
        return self._line_edit

    def _get_display_text(self, layer: Layer) -> str:
        return layer.name


class TestFileComponentBaseLifecycle:
    def test_clear_shows_placeholder(self, parent_widget: QWidget):
        component = _DummyFileComponent(parent_widget)

        component.clear()

        assert component.value_widget.text() == ''
        assert len(component.get_text_calls) == 0

    def test_load_entries_updates_display_and_tooltip(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = _DummyFileComponent(parent_widget)

        component.load_entries(layer)

        assert component.value_widget.text() == 'shape=(4, 3)'
        assert len(component.get_text_calls) == 1
        assert component.value_widget.toolTip() == 'File tooltip.'

    def test_default_value_widget_is_display_label(
        self, parent_widget: QWidget
    ):
        component = _DummyFileComponent(parent_widget)

        assert component.value_widget is component._display_label

    def test_load_entries_tooltip_on_custom_value_widget(
        self, parent_widget: QWidget
    ):
        layer = Image(np.zeros((4, 3)))
        component = _DummyFileComponentWithLineEdit(parent_widget)

        component.load_entries(layer)

        assert component.value_widget.toolTip() == 'Line edit tooltip.'
