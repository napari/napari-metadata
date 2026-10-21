"""Tests for all scale bar components and their coordinator."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from napari.components._viewer_constants import CanvasPosition

from napari_metadata.viewer_widgets._base import ViewerComponentBase
from napari_metadata.viewer_widgets._scale_bar import (
    ScaleBarBox,
    ScaleBarColor,
    ScaleBarFixedLength,
    ScaleBarFontSize,
    ScaleBarMetadata,
    ScaleBarOpacity,
    ScaleBarPosition,
    ScaleBarTicks,
    ScaleBarVisible,
    _supports_auto_box_color,
    get_scale_bar,
)

requires_auto_box_color = pytest.mark.skipif(
    not _supports_auto_box_color(),
    reason='automatic box color (box_color=None) was added in napari 0.7.0',
)


class _DummyScaleBarComponent(ViewerComponentBase):
    """Test double for verifying coordinator-level lifecycle."""

    _label_text = 'Dummy:'

    def __init__(self, viewer_model, parent_widget) -> None:
        super().__init__(viewer_model, parent_widget)
        self.load_calls = 0
        self.loaded_viewers = []

    def load_entries(self, viewer=None) -> None:
        self.load_calls += 1
        self.loaded_viewers.append(
            viewer if viewer is not None else self._napari_viewer
        )
        super().load_entries(viewer)

    def _get_display_text(self) -> str:
        return 'dummy'


class TestGetScaleBar:
    def test_falls_back_to_legacy_attribute_on_old_napari(self):
        legacy_scale_bar = object()
        old_viewer = SimpleNamespace(scale_bar=legacy_scale_bar)

        assert get_scale_bar(old_viewer) is legacy_scale_bar


class TestScaleBarVisible:
    def test_load_entries_reflects_viewer_scale_bar_visibility(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).visible = True
        component = ScaleBarVisible(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].isChecked() is True

    def test_load_entries_applies_tooltip_to_toggle(
        self, viewer_model, parent_widget
    ):
        component = ScaleBarVisible(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Show or hide the viewer scale bar overlay.'
        )

    def test_toggle_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).visible = False
        component = ScaleBarVisible(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setChecked(True)

        assert get_scale_bar(viewer_model).visible is True

    def test_clear_turns_toggle_off(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).visible = True
        component = ScaleBarVisible(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].isChecked() is False


class TestScaleBarFontSize:
    def test_load_entries_reflects_viewer_font_size(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).font_size = 14.0
        component = ScaleBarFontSize(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].value() == 14.0

    def test_load_entries_applies_tooltip(self, viewer_model, parent_widget):
        component = ScaleBarFontSize(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Font size of the units text displayed on the scale bar.'
        )

    def test_spinbox_writes_back_to_viewer(self, viewer_model, parent_widget):
        component = ScaleBarFontSize(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setValue(16.0)

        assert get_scale_bar(viewer_model).font_size == 16.0

    def test_clear_resets_to_default(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).font_size = 24.0
        component = ScaleBarFontSize(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].value() == 10.0


class TestScaleBarFixedLength:
    def test_load_entries_reflects_viewer_length(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).length = 100.0
        component = ScaleBarFixedLength(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].value() == 100.0

    def test_load_entries_checks_auto_when_length_is_none(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).length = None
        component = ScaleBarFixedLength(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[1].isChecked() is True
        assert component.value_widgets[0].isEnabled() is False

    def test_spinbox_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).length = 50.0
        component = ScaleBarFixedLength(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setValue(75.0)

        assert get_scale_bar(viewer_model).length == 75.0

    def test_auto_checkbox_sets_length_to_none(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).length = 50.0
        component = ScaleBarFixedLength(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[1].setChecked(True)

        assert get_scale_bar(viewer_model).length is None
        assert component.value_widgets[0].isEnabled() is False

    def test_unchecking_auto_restores_length(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).length = None
        component = ScaleBarFixedLength(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setValue(30.0)
        component.value_widgets[1].setChecked(False)

        assert get_scale_bar(viewer_model).length == 30.0
        assert component.value_widgets[0].isEnabled() is True

    def test_clear_resets_to_default(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).length = 200.0
        component = ScaleBarFixedLength(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[1].isChecked() is False
        assert component.value_widgets[0].value() == 50.0


class TestScaleBarColor:
    def test_load_entries_reflects_viewer_color(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).colored = True
        get_scale_bar(viewer_model).color = 'red'
        component = ScaleBarColor(viewer_model, parent_widget)

        component.load_entries()

        assert not component.value_widgets[1].isChecked()

    def test_load_entries_checks_auto_when_not_colored(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).colored = False
        component = ScaleBarColor(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[1].isChecked()

    def test_auto_checkbox_toggles_colored(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).colored = True
        component = ScaleBarColor(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[1].setChecked(True)

        assert get_scale_bar(viewer_model).colored is False

    def test_unchecking_auto_reenables_colored(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).colored = False
        component = ScaleBarColor(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[1].setChecked(False)

        assert get_scale_bar(viewer_model).colored is True

    def test_clear_resets_to_default(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).colored = False
        component = ScaleBarColor(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[1].isChecked() is False


class TestScaleBarBox:
    def test_load_entries_reflects_box_visibility(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).box = True
        component = ScaleBarBox(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].isChecked() is True

    @requires_auto_box_color
    def test_load_entries_checks_auto_when_box_color_none(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).box = True
        get_scale_bar(viewer_model).box_color = None
        component = ScaleBarBox(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[2].isChecked() is True

    def test_toggle_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).box = False
        component = ScaleBarBox(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setChecked(True)

        assert get_scale_bar(viewer_model).box is True

    @requires_auto_box_color
    def test_auto_checkbox_sets_box_color_to_none(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).box = True
        get_scale_bar(viewer_model).box_color = 'red'
        component = ScaleBarBox(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[2].setChecked(True)

        assert get_scale_bar(viewer_model).box_color is None

    def test_no_auto_checkbox_without_napari_support(
        self, viewer_model, parent_widget, monkeypatch
    ):
        monkeypatch.setattr(
            'napari_metadata.viewer_widgets._scale_bar._supports_auto_box_color',
            lambda: False,
        )
        component = ScaleBarBox(viewer_model, parent_widget)
        component.load_entries()

        assert len(component.value_widgets) == 2

    def test_clear_resets_toggle_to_off(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).box = True
        component = ScaleBarBox(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].isChecked() is False


class TestScaleBarTicks:
    def test_load_entries_reflects_viewer_ticks(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).ticks = True
        component = ScaleBarTicks(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].isChecked() is True

    def test_load_entries_applies_tooltip(self, viewer_model, parent_widget):
        component = ScaleBarTicks(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Show or hide the ticks at the ends of the scale bar.'
        )

    def test_toggle_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).ticks = False
        component = ScaleBarTicks(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setChecked(True)

        assert get_scale_bar(viewer_model).ticks is True

    def test_clear_turns_toggle_off(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).ticks = True
        component = ScaleBarTicks(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].isChecked() is False


class TestScaleBarOpacity:
    def test_load_entries_reflects_viewer_opacity(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).opacity = 0.5
        component = ScaleBarOpacity(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].value() == 0.5
        assert component.value_widgets[1].value() == 0.5

    def test_load_entries_applies_tooltip(self, viewer_model, parent_widget):
        component = ScaleBarOpacity(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Set the opacity of the scale bar.'
        )

    def test_slider_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).opacity = 1.0
        component = ScaleBarOpacity(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setValue(0.3)

        assert get_scale_bar(viewer_model).opacity == 0.3

    def test_spinbox_writes_back_to_viewer(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).opacity = 1.0
        component = ScaleBarOpacity(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[1].setValue(0.7)

        assert get_scale_bar(viewer_model).opacity == 0.7

    def test_slider_and_spinbox_stay_synced(self, viewer_model, parent_widget):
        component = ScaleBarOpacity(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setValue(0.25)

        assert component.value_widgets[1].value() == 0.25

    def test_clear_resets_to_one(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).opacity = 0.3
        component = ScaleBarOpacity(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].value() == 1.0
        assert component.value_widgets[1].value() == 1.0


class TestScaleBarPosition:
    def test_load_entries_reflects_viewer_position(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).position = CanvasPosition.TOP_LEFT
        component = ScaleBarPosition(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].currentEnum() == CanvasPosition.TOP_LEFT
        )

    def test_load_entries_applies_tooltip(self, viewer_model, parent_widget):
        component = ScaleBarPosition(viewer_model, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Set the position of the scale bar.'
        )

    def test_position_change_writes_back_to_viewer(
        self, viewer_model, parent_widget
    ):
        get_scale_bar(viewer_model).position = CanvasPosition.BOTTOM_RIGHT
        component = ScaleBarPosition(viewer_model, parent_widget)
        component.load_entries()

        component.value_widgets[0].setCurrentEnum(CanvasPosition.TOP_LEFT)

        assert get_scale_bar(viewer_model).position == CanvasPosition.TOP_LEFT

    def test_clear_resets_to_bottom_right(self, viewer_model, parent_widget):
        get_scale_bar(viewer_model).position = CanvasPosition.TOP_LEFT
        component = ScaleBarPosition(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert (
            component.value_widgets[0].currentEnum()
            == CanvasPosition.BOTTOM_RIGHT
        )


class TestScaleBarMetadata:
    def test_default_components_contains_visibility_component(
        self, viewer_model, parent_widget
    ):
        coordinator = ScaleBarMetadata(viewer_model, parent_widget)

        components = coordinator.components
        assert [type(component) for component in components] == [
            ScaleBarVisible,
            ScaleBarFixedLength,
            ScaleBarPosition,
            ScaleBarTicks,
            ScaleBarFontSize,
            ScaleBarColor,
            ScaleBarBox,
            ScaleBarOpacity,
        ]

    def test_components_returns_display_order(
        self, viewer_model, parent_widget
    ):
        component_a = _DummyScaleBarComponent(viewer_model, parent_widget)
        component_b = _DummyScaleBarComponent(viewer_model, parent_widget)
        coordinator = ScaleBarMetadata(
            viewer_model,
            parent_widget,
            components=[component_a, component_b],
        )

        assert coordinator.components == [component_a, component_b]
        assert coordinator.components is not coordinator._components

    def test_refresh_loads_all_components(self, viewer_model, parent_widget):
        component_a = _DummyScaleBarComponent(viewer_model, parent_widget)
        component_b = _DummyScaleBarComponent(viewer_model, parent_widget)
        coordinator = ScaleBarMetadata(
            viewer_model,
            parent_widget,
            components=[component_a, component_b],
        )

        coordinator.refresh()

        assert component_a.load_calls == 1
        assert component_b.load_calls == 1
        assert component_a.loaded_viewers == [viewer_model]
        assert component_b.loaded_viewers == [viewer_model]

    def test_visible_event_refreshes_visibility_component(
        self, viewer_model, parent_widget
    ):
        coordinator = ScaleBarMetadata(viewer_model, parent_widget)
        visibility_component = coordinator._scale_bar_visible
        initial_checked = visibility_component.value_widgets[0].isChecked()

        scale_bar = get_scale_bar(viewer_model)
        scale_bar.visible = not scale_bar.visible

        assert (
            visibility_component.value_widgets[0].isChecked()
            is not initial_checked
        )
        assert visibility_component.value_widgets[0].isChecked() is (
            scale_bar.visible
        )
