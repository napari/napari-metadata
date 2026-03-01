"""Behavior tests for MetadataWidget orientation unification.

Tests cover:
* Widget construction and page management
* Content rebuild for both vertical and horizontal orientations
* File grid population for both orientations
* Axis grid population for both orientations
* Separator helpers
* Layer change triggers content rebuild
* Detach/reparent of persistent component widgets
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from qtpy.QtWidgets import QFrame, QGridLayout, QWidget

from napari_metadata.widgets._main import (
    _CONTENT_PAGE,
    _NO_LAYER_PAGE,
    MetadataWidget,
    Orientation,
    _add_horizontal_separator,
    _add_vertical_separator,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel


@pytest.fixture
def viewer_with_layer(viewer_model: ViewerModel):
    """ViewerModel with a single 2D image layer added."""
    layer = viewer_model.add_image(
        np.zeros((4, 3)),
        name='test',
        axis_labels=('y', 'x'),
        scale=(1.0, 1.0),
        translate=(0.0, 0.0),
        units=('pixel', 'pixel'),
    )
    return viewer_model, layer


@pytest.fixture
def metadata_widget(
    viewer_model: ViewerModel, parent_widget: QWidget, qtbot
) -> MetadataWidget:
    """A MetadataWidget instance (not shown, no QDockWidget parent)."""
    widget = MetadataWidget(viewer_model)
    widget.setParent(parent_widget)
    qtbot.addWidget(widget)
    return widget


class TestMetadataWidgetInit:
    def test_stacked_layout_has_two_pages(
        self, metadata_widget: MetadataWidget
    ):
        assert metadata_widget._stacked_layout.count() == 2

    def test_starts_with_no_scroll_area(self, metadata_widget: MetadataWidget):
        assert metadata_widget._scroll_area is None

    def test_starts_with_no_orientation(self, metadata_widget: MetadataWidget):
        assert metadata_widget._current_orientation is None

    def test_starts_with_no_selected_layer(
        self, metadata_widget: MetadataWidget
    ):
        assert metadata_widget._selected_layer is None

    def test_starts_on_no_layer_page(self, metadata_widget: MetadataWidget):
        assert metadata_widget._stacked_layout.currentIndex() == _NO_LAYER_PAGE

    def test_has_general_metadata_instance(
        self, metadata_widget: MetadataWidget
    ):
        assert metadata_widget._general_metadata_instance is not None
        assert len(metadata_widget._general_metadata_instance.components) == 5

    def test_has_axis_metadata_instance(self, metadata_widget: MetadataWidget):
        assert metadata_widget._axis_metadata_instance is not None
        assert len(metadata_widget._axis_metadata_instance.components) == 4

    def test_has_inheritance_instance(self, metadata_widget: MetadataWidget):
        assert metadata_widget._inheritance_instance is not None


class TestPageManagement:
    def test_refresh_page_shows_no_layer_when_none_selected(
        self, metadata_widget: MetadataWidget
    ):
        metadata_widget._selected_layer = None
        metadata_widget._refresh_page()

        assert metadata_widget._stacked_layout.currentIndex() == _NO_LAYER_PAGE
        assert metadata_widget._current_orientation is None

    def test_refresh_page_shows_content_when_layer_selected(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)

        widget._selected_layer = layer
        widget._refresh_page()

        assert widget._stacked_layout.currentIndex() == _CONTENT_PAGE
        assert widget._current_orientation is not None


class TestRebuildContent:
    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_rebuild_creates_scroll_area(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
        orientation: Orientation,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content(orientation)

        assert widget._scroll_area is not None
        assert widget._current_orientation == orientation

    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_rebuild_creates_inheritance_section(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
        orientation: Orientation,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content(orientation)

        assert widget._inheritance_section is not None

    def test_rebuild_replaces_old_scroll_area(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        first_scroll = widget._scroll_area

        widget._rebuild_content('horizontal')
        second_scroll = widget._scroll_area

        assert first_scroll is not second_scroll

    def test_rebuild_is_reentrant_safe(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuilding = True
        widget._rebuild_content('vertical')
        # Should be a no-op — _scroll_area stays None
        assert widget._scroll_area is None
        widget._rebuilding = False


class TestDetachComponentWidgets:
    def test_detach_reparents_file_components(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        # Build content to place widgets into containers
        widget._rebuild_content('vertical')

        # Now detach
        widget._detach_component_widgets()

        for comp in widget._general_metadata_instance.components:
            assert comp.component_label.parent() is widget
            assert comp.value_widget.parent() is widget

    def test_detach_reparents_axis_components(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        widget._detach_component_widgets()

        for comp in widget._axis_metadata_instance.components:
            assert comp.component_label.parent() is widget

    def test_detach_reparents_inheritance_widget(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        widget._detach_component_widgets()

        assert widget._inheritance_instance.parent() is widget


class TestOrientationSwitching:
    def test_vertical_then_horizontal_preserves_component_instances(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        general_id = id(widget._general_metadata_instance)
        axis_id = id(widget._axis_metadata_instance)
        inheritance_id = id(widget._inheritance_instance)

        widget._rebuild_content('horizontal')

        # Instances are the same objects — not recreated
        assert id(widget._general_metadata_instance) == general_id
        assert id(widget._axis_metadata_instance) == axis_id
        assert id(widget._inheritance_instance) == inheritance_id

    def test_vertical_uses_vertical_scroll(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        from qtpy.QtWidgets import QScrollArea

        from napari_metadata.widgets._containers import (
            HorizontalOnlyOuterScrollArea,
        )

        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        assert isinstance(widget._scroll_area, QScrollArea)
        assert not isinstance(
            widget._scroll_area, HorizontalOnlyOuterScrollArea
        )

    def test_horizontal_uses_horizontal_scroll(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        from napari_metadata.widgets._containers import (
            HorizontalOnlyOuterScrollArea,
        )

        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('horizontal')
        assert isinstance(widget._scroll_area, HorizontalOnlyOuterScrollArea)


class TestLayerSelectionFlow:
    def test_selecting_layer_triggers_content_build(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)

        assert widget._scroll_area is None

        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget._selected_layer = layer
        widget._refresh_page()

        assert widget._scroll_area is not None
        assert widget._stacked_layout.currentIndex() == _CONTENT_PAGE

    def test_deselecting_layer_shows_no_layer_page(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)

        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget._selected_layer = layer
        widget._refresh_page()

        widget._selected_layer = None
        widget._refresh_page()

        assert widget._stacked_layout.currentIndex() == _NO_LAYER_PAGE

    def test_switching_layers_rebuilds_content(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)

        layer_a = viewer_model.add_image(
            np.zeros((4, 3)), name='a', axis_labels=('y', 'x')
        )
        widget._selected_layer = layer_a
        widget._refresh_page()
        first_scroll = widget._scroll_area

        layer_b = viewer_model.add_image(
            np.zeros((5, 5, 5)), name='b', axis_labels=('z', 'y', 'x')
        )
        widget._selected_layer = layer_b
        widget._refresh_page()
        second_scroll = widget._scroll_area

        # New scroll area was created (content rebuilt)
        assert first_scroll is not second_scroll


class TestInheritanceCheckboxSync:
    def test_checkboxes_hidden_after_rebuild_when_section_collapsed(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        widget._rebuild_content('vertical')
        assert widget._inheritance_section is not None

        # Expand inheritance once so checkbox visibility is turned on.
        widget._inheritance_section._button.setChecked(True)
        assert all(
            all(not cb.isHidden() for cb in comp._inherit_checkboxes)
            for comp in widget._axis_metadata_instance.components
        )

        # Rebuild creates a new collapsed inheritance section; checkboxes
        # must be synchronized back to hidden.
        widget._refresh_page()
        assert widget._inheritance_section is not None
        assert not widget._inheritance_section.isExpanded()
        assert all(
            all(cb.isHidden() for cb in comp._inherit_checkboxes)
            for comp in widget._axis_metadata_instance.components
        )


class TestFileGridPopulation:
    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_file_grid_has_five_component_labels(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
        orientation: Orientation,
    ):
        layer = viewer_model.add_image(np.zeros((4, 3)), name='test')
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        container = QWidget(parent_widget)
        grid = QGridLayout(container)
        widget._populate_file_grid(grid, orientation)

        # Grid should have at least 5 rows for the 5 file components
        # (more for vertical because _under_label_in_vertical adds rows)
        assert grid.count() >= 10  # 5 labels + 5 values


class TestAxisGridPopulation:
    def test_vertical_axis_grid_populates(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        container = QWidget(parent_widget)
        grid = QGridLayout(container)
        widget._populate_axis_grid(grid, 'vertical')

        # Grid should contain widgets
        assert grid.count() > 0

    def test_horizontal_axis_grid_populates(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
            scale=(1.0, 1.0),
            translate=(0.0, 0.0),
            units=('pixel', 'pixel'),
        )
        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = layer

        container = QWidget(parent_widget)
        grid = QGridLayout(container)
        widget._populate_axis_grid(grid, 'horizontal')

        assert grid.count() > 0


class TestSeparatorHelpers:
    def test_horizontal_separator_adds_three_widgets(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        grid = QGridLayout(container)

        _add_horizontal_separator(grid, 0, 3)

        # 3 widgets: before padding, line, after padding
        assert grid.count() == 3

    def test_horizontal_separator_line_is_hline(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        grid = QGridLayout(container)

        _add_horizontal_separator(grid, 0, 3)

        # The second widget (index 1) is the QFrame line
        line_item = grid.itemAtPosition(1, 0)
        assert line_item is not None
        line = line_item.widget()
        assert isinstance(line, QFrame)
        assert line.frameShape() == QFrame.Shape.HLine

    def test_vertical_separator_adds_three_widgets(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        grid = QGridLayout(container)

        _add_vertical_separator(grid, 0, 3)

        assert grid.count() == 3

    def test_vertical_separator_line_is_vline(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        grid = QGridLayout(container)

        _add_vertical_separator(grid, 0, 3)

        # The second widget (column 1) is the QFrame line
        line_item = grid.itemAtPosition(0, 1)
        assert line_item is not None
        line = line_item.widget()
        assert isinstance(line, QFrame)
        assert line.frameShape() == QFrame.Shape.VLine


class TestGetRequiredOrientation:
    def test_defaults_to_vertical_without_dock_parent(
        self, metadata_widget: MetadataWidget
    ):
        # No QDockWidget parent — should default to vertical
        assert metadata_widget._get_required_orientation() == 'vertical'


class TestGetDockWidget:
    def test_returns_none_without_dock_parent(
        self, metadata_widget: MetadataWidget
    ):
        assert metadata_widget.get_dock_widget() is None


class TestApplyInheritance:
    def test_inheritance_applies_template_values(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        current = viewer_model.add_image(
            np.zeros((4, 3)),
            translate=(1.0, 2.0),
            scale=(1.0, 1.0),
            units=('pixel', 'pixel'),
        )
        template = viewer_model.add_image(
            np.zeros((4, 3)),
            translate=(10.0, 20.0),
            scale=(5.0, 5.0),
            units=('meter', 'meter'),
        )

        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = current
        widget._rebuild_content('vertical')

        viewer_model.layers.selection.active = current

        # Check all inheritance checkboxes
        for comp in widget._axis_metadata_instance.components:
            for cb in comp._inherit_checkboxes:
                cb.setChecked(True)

        widget.apply_inheritance_to_current_layer(template)

        assert tuple(current.translate) == pytest.approx((10.0, 20.0))
        assert tuple(current.scale) == pytest.approx((5.0, 5.0))

    def test_inheritance_rejects_dimension_mismatch(
        self,
        viewer_model: ViewerModel,
        parent_widget: QWidget,
        qtbot,
    ):
        current = viewer_model.add_image(np.zeros((4, 3)))
        template = viewer_model.add_image(np.zeros((5, 5, 5)))

        widget = MetadataWidget(viewer_model)
        widget.setParent(parent_widget)
        qtbot.addWidget(widget)
        widget._selected_layer = current
        widget._rebuild_content('vertical')

        viewer_model.layers.selection.active = current
        original_translate = tuple(current.translate)

        widget.apply_inheritance_to_current_layer(template)

        # Should be unchanged
        assert tuple(current.translate) == pytest.approx(original_translate)
