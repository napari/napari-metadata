"""Tests for InheritanceWidget callback lifecycle and close-event cleanup.

Tests cover:
* Initial state with no layers
* Combobox population when layers are added/removed
* close() disconnects list-events so the combobox is no longer updated
* close() disconnects selection-events so the inheriting label is no longer updated
* close() disconnects layer name-changed callback when a layer is selected
* close() does NOT raise when no layer is selected (None guard)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from napari_metadata.widgets._inheritance import InheritanceWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from qtpy.QtWidgets import QWidget


@pytest.fixture
def inheritance_widget(
    viewer_model: ViewerModel, parent_widget: QWidget, qtbot
) -> InheritanceWidget:
    widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
    qtbot.addWidget(widget)
    return widget


class TestInheritanceWidgetInit:
    def test_combobox_empty_with_no_layers(
        self, inheritance_widget: InheritanceWidget
    ) -> None:
        assert inheritance_widget._template_combobox.count() == 0

    def test_inheriting_label_shows_none_with_no_selection(
        self, inheritance_widget: InheritanceWidget
    ) -> None:
        assert (
            inheritance_widget._inheriting_layer_name.text() == 'None selected'
        )

    def test_apply_button_disabled_with_no_layers(
        self, inheritance_widget: InheritanceWidget
    ) -> None:
        assert not inheritance_widget._apply_button.isEnabled()

    def test_selected_layer_is_none_at_init(
        self, inheritance_widget: InheritanceWidget
    ) -> None:
        assert inheritance_widget._selected_layer is None


class TestComboboxPopulation:
    def test_combobox_gains_entry_when_layer_added(
        self,
        viewer_model: ViewerModel,
        inheritance_widget: InheritanceWidget,
    ) -> None:
        # Before: no items
        assert inheritance_widget._template_combobox.count() == 0
        viewer_model.add_image(np.zeros((4, 4)), name='test-layer')
        # After: 'None' placeholder + 'test-layer'
        assert inheritance_widget._template_combobox.count() == 2

    def test_combobox_loses_entry_when_layer_removed(
        self,
        viewer_model: ViewerModel,
        inheritance_widget: InheritanceWidget,
    ) -> None:
        layer = viewer_model.add_image(np.zeros((4, 4)), name='layer-a')
        assert inheritance_widget._template_combobox.count() == 2
        viewer_model.layers.remove(layer)
        # No layers → combobox should be empty
        assert inheritance_widget._template_combobox.count() == 0

    def test_combobox_updates_when_layer_renamed(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """Renaming the active layer should update the combobox items."""
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        layer = viewer_model.add_image(np.zeros((4, 4)), name='original')
        layer.name = 'renamed'
        items = [
            widget._template_combobox.itemText(i)
            for i in range(widget._template_combobox.count())
        ]
        assert 'renamed' in items
        assert 'original' not in items


class TestApplyButton:
    def test_enabled_when_template_and_inheriting_differ_same_ndim(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        viewer_model.add_image(np.zeros((4, 4)), name='template')
        viewer_model.add_image(np.zeros((4, 4)), name='inheriting')
        # Select 'template' in combobox (index 0='None', 1='template', 2='inheriting')
        widget._template_combobox.setCurrentIndex(1)
        # Active layer is 'inheriting' (last added)
        assert widget._apply_button.isEnabled()
        assert widget._different_dims_label.isHidden()

    def test_disabled_when_template_is_none(
        self,
        viewer_model: ViewerModel,
        inheritance_widget: InheritanceWidget,
    ) -> None:
        viewer_model.add_image(np.zeros((4, 4)), name='layer')
        # Combobox defaults to 'None' placeholder
        inheritance_widget._template_combobox.setCurrentIndex(0)
        assert not inheritance_widget._apply_button.isEnabled()

    def test_disabled_when_same_layer_selected(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        viewer_model.add_image(np.zeros((4, 4)), name='only-layer')
        # Select the same layer as template
        widget._template_combobox.setCurrentIndex(1)
        # Active is also 'only-layer' → same object
        assert not widget._apply_button.isEnabled()

    def test_disabled_with_dim_mismatch_and_warning_visible(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        viewer_model.add_image(np.zeros((4, 4)), name='2d-layer')
        viewer_model.add_image(np.zeros((3, 4, 4)), name='3d-layer')
        # Template = '2d-layer', inheriting (active) = '3d-layer'
        widget._template_combobox.setCurrentIndex(1)
        assert not widget._apply_button.isEnabled()
        assert not widget._different_dims_label.isHidden()

    def test_apply_invokes_callback_with_template_layer(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        received = []
        widget = InheritanceWidget(
            viewer_model.layers,
            on_apply_inheritance=received.append,
            parent=parent_widget,
        )
        qtbot.addWidget(widget)
        template = viewer_model.add_image(np.zeros((4, 4)), name='template')
        viewer_model.add_image(np.zeros((4, 4)), name='inheriting')
        widget._template_combobox.setCurrentIndex(1)
        widget._apply_button.click()
        assert received == [template]

    def test_apply_noop_when_dims_mismatch(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        received = []
        widget = InheritanceWidget(
            viewer_model.layers,
            on_apply_inheritance=received.append,
            parent=parent_widget,
        )
        qtbot.addWidget(widget)
        viewer_model.add_image(np.zeros((4, 4)), name='2d')
        viewer_model.add_image(np.zeros((3, 4, 4)), name='3d')
        widget._template_combobox.setCurrentIndex(1)
        widget._apply_button.click()
        assert received == []


class TestCloseDisconnectsListEvents:
    def test_combobox_not_updated_after_close(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """After close(), adding a layer must NOT update the combobox."""
        viewer_model.add_image(np.zeros((4, 4)), name='existing')
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        assert widget._template_combobox.count() == 2  # None + existing

        widget.close()
        count_at_close = widget._template_combobox.count()

        # Adding a layer after close should leave the combobox untouched
        viewer_model.add_image(np.zeros((3, 3)), name='new-layer')
        assert widget._template_combobox.count() == count_at_close

    def test_combobox_not_updated_after_close_on_remove(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """After close(), removing a layer must NOT update the combobox."""
        layer = viewer_model.add_image(np.zeros((4, 4)), name='to-remove')
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        count_at_close = widget._template_combobox.count()

        widget.close()

        viewer_model.layers.remove(layer)
        assert widget._template_combobox.count() == count_at_close


class TestCloseDisconnectsSelectionEvents:
    def test_inheriting_label_not_updated_after_close(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """After close(), changing the active layer must NOT update the label."""
        layer1 = viewer_model.add_image(np.zeros((4, 4)), name='layer1')
        layer2 = viewer_model.add_image(np.zeros((4, 4)), name='layer2')
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)

        # Make layer1 active so the label reflects it before close
        viewer_model.layers.selection.active = layer1
        assert widget._inheriting_layer_name.text() == 'layer1'

        widget.close()
        label_at_close = widget._inheriting_layer_name.text()

        # Switching to layer2 after close should leave the label untouched
        viewer_model.layers.selection.active = layer2
        assert widget._inheriting_layer_name.text() == label_at_close


class TestCloseDisconnectsLayerNameCallback:
    def test_combobox_not_updated_on_rename_after_close(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """After close(), renaming the selected layer must NOT update the combobox."""
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)

        # Adding a layer auto-selects it, which wires the name-changed callback
        layer = viewer_model.add_image(np.zeros((4, 4)), name='before-close')
        assert widget._selected_layer is layer

        widget.close()

        # After close, renaming should not update the (frozen) combobox
        layer.name = 'after-close'
        items = [
            widget._template_combobox.itemText(i)
            for i in range(widget._template_combobox.count())
        ]
        assert 'after-close' not in items

    def test_close_safe_when_no_selected_layer(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ) -> None:
        """close() must not raise when _selected_layer is None."""
        widget = InheritanceWidget(viewer_model.layers, parent=parent_widget)
        qtbot.addWidget(widget)
        assert widget._selected_layer is None
        # Should complete without error
        widget.close()
