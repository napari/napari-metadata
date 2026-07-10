"""Behavior tests for ViewerMetadataWidget.

Tests cover:
* Widget construction
* Content rebuild for both vertical and horizontal orientations
* Section expand/collapse toggle
* Teardown/rebuild cycle (orientation switching)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from qtpy.QtWidgets import QWidget

from napari_metadata.viewer_widgets._viewer_metadata import (
    ViewerMetadataWidget,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel


def _assert_section_content_available(widget: ViewerMetadataWidget) -> None:
    assert widget._dims_section is not None
    assert widget._scale_bar_section is not None

    for section in (
        widget._dims_section,
        widget._scale_bar_section,
    ):
        assert section._expanding_area is not None
        assert section._expanding_area.sizeHint().isValid()
        assert section.sizeHint().width() > 0
        assert section.sizeHint().height() > 0


@pytest.fixture
def viewer_with_data(viewer_model: ViewerModel):
    """ViewerModel with a 3D image layer added (so dims has 3 axes)."""
    viewer_model.add_image(
        np.zeros((2, 4, 3)),
        name='test',
        axis_labels=('z', 'y', 'x'),
    )
    return viewer_model


@pytest.fixture
def viewer_metadata_widget(
    viewer_model: ViewerModel, parent_widget: QWidget, qtbot
) -> ViewerMetadataWidget:
    """A ViewerMetadataWidget instance (not shown, no QDockWidget parent)."""
    widget = ViewerMetadataWidget(viewer_model)
    widget.setParent(parent_widget)
    qtbot.addWidget(widget)
    return widget


class TestViewerMetadataWidgetConstruction:
    def test_creates_sections(self, viewer_metadata_widget):
        assert viewer_metadata_widget._dims_section is not None
        assert viewer_metadata_widget._scale_bar_section is not None

    def test_sections_start_collapsed(self, viewer_metadata_widget):
        assert not viewer_metadata_widget._dims_section.isExpanded()
        assert not viewer_metadata_widget._scale_bar_section.isExpanded()

    def test_initial_orientation_is_vertical(self, viewer_metadata_widget):
        assert viewer_metadata_widget._current_orientation == 'vertical'

    def test_size_hints_are_valid(self, viewer_metadata_widget):
        assert viewer_metadata_widget.sizeHint().isValid()
        assert viewer_metadata_widget.minimumSizeHint().isValid()

    def test_section_label_text_matches(self, viewer_metadata_widget):
        assert (
            'Viewer dims'
            in viewer_metadata_widget._dims_section._button.text()
        )
        assert (
            'Scale bar'
            in viewer_metadata_widget._scale_bar_section._button.text()
        )


class TestRebuildContent:
    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_rebuild_creates_scroll_area(
        self,
        viewer_metadata_widget,
        orientation: str,
    ):
        viewer_metadata_widget._rebuild_content(orientation)
        # Expand sections so content is visible
        viewer_metadata_widget._dims_section.setExpanded(True)
        viewer_metadata_widget._scale_bar_section.setExpanded(True)

        assert viewer_metadata_widget._scroll_area is not None
        assert viewer_metadata_widget._content_widget is not None
        assert viewer_metadata_widget._dims_section is not None
        assert viewer_metadata_widget._scale_bar_section is not None
        _assert_section_content_available(viewer_metadata_widget)

    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_rebuild_preserves_expanded_state(
        self,
        viewer_metadata_widget,
        orientation: str,
    ):
        viewer_metadata_widget._rebuild_content('vertical')
        viewer_metadata_widget._dims_section.setExpanded(True)
        viewer_metadata_widget._scale_bar_section.setExpanded(True)

        viewer_metadata_widget._rebuild_content(orientation)

        assert viewer_metadata_widget._dims_section.isExpanded() is True
        assert viewer_metadata_widget._scale_bar_section.isExpanded() is True

    @pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
    def test_rebuild_preserves_components_across_teardown(
        self,
        viewer_metadata_widget,
        orientation: str,
    ):
        dims = viewer_metadata_widget._dims_instance
        scale_bar = viewer_metadata_widget._scale_bar_instance

        viewer_metadata_widget._rebuild_content(orientation)

        assert viewer_metadata_widget._dims_instance is dims
        assert viewer_metadata_widget._scale_bar_instance is scale_bar

    def test_double_rebuild_is_idempotent(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('vertical')
        first_scroll = viewer_metadata_widget._scroll_area

        viewer_metadata_widget._rebuild_content('vertical')
        second_scroll = viewer_metadata_widget._scroll_area

        assert second_scroll is not None
        assert second_scroll is not first_scroll


class TestSectionToggle:
    def test_toggling_dims_section_triggers_size_update(
        self, viewer_metadata_widget
    ):
        viewer_metadata_widget._rebuild_content('vertical')
        assert not viewer_metadata_widget._dims_section.isExpanded()

        viewer_metadata_widget._dims_section.setExpanded(True)

        assert viewer_metadata_widget._dims_section.isExpanded() is True

    def test_teardown_saves_expanded_state_of_dims_section(
        self, viewer_metadata_widget
    ):
        viewer_metadata_widget._rebuild_content('vertical')
        viewer_metadata_widget._dims_section.setExpanded(True)

        viewer_metadata_widget._teardown_content()

        assert viewer_metadata_widget._dims_expanded is True

    def test_toggling_scale_bar_section_triggers_size_update(
        self, viewer_metadata_widget
    ):
        viewer_metadata_widget._rebuild_content('vertical')
        assert not viewer_metadata_widget._scale_bar_section.isExpanded()

        viewer_metadata_widget._scale_bar_section.setExpanded(True)

        assert viewer_metadata_widget._scale_bar_section.isExpanded() is True


class TestOrientationSwitching:
    def test_rebuild_from_vertical_to_horizontal(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('vertical')
        assert viewer_metadata_widget._current_orientation == 'vertical'

        viewer_metadata_widget._rebuild_content('horizontal')
        assert viewer_metadata_widget._current_orientation == 'horizontal'
        assert viewer_metadata_widget._scroll_area is not None

    def test_rebuild_from_horizontal_to_vertical(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('horizontal')
        assert viewer_metadata_widget._current_orientation == 'horizontal'

        viewer_metadata_widget._rebuild_content('vertical')
        assert viewer_metadata_widget._current_orientation == 'vertical'

    def test_same_orientation_does_not_teardown(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('vertical')
        first_sections = (
            viewer_metadata_widget._dims_section,
            viewer_metadata_widget._scale_bar_section,
        )

        viewer_metadata_widget._rebuild_content('vertical')
        second_sections = (
            viewer_metadata_widget._dims_section,
            viewer_metadata_widget._scale_bar_section,
        )

        # Sections are recreated, so they're different objects
        assert second_sections[0] is not first_sections[0]
        assert second_sections[1] is not first_sections[1]


class TestTeardownContent:
    def test_teardown_clears_scroll_area(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('vertical')
        assert viewer_metadata_widget._scroll_area is not None

        viewer_metadata_widget._teardown_content()

        assert viewer_metadata_widget._scroll_area is None
        assert viewer_metadata_widget._dims_section is None
        assert viewer_metadata_widget._scale_bar_section is None

    def test_teardown_saves_expanded_states(self, viewer_metadata_widget):
        viewer_metadata_widget._rebuild_content('vertical')
        viewer_metadata_widget._dims_section.setExpanded(True)

        viewer_metadata_widget._teardown_content()

        assert viewer_metadata_widget._dims_expanded is True
        assert viewer_metadata_widget._scale_bar_expanded is False

    def test_teardown_preserves_component_instances(
        self, viewer_metadata_widget
    ):
        viewer_metadata_widget._rebuild_content('vertical')
        dims = viewer_metadata_widget._dims_instance
        scale_bar = viewer_metadata_widget._scale_bar_instance

        viewer_metadata_widget._teardown_content()

        assert viewer_metadata_widget._dims_instance is dims
        assert viewer_metadata_widget._scale_bar_instance is scale_bar
