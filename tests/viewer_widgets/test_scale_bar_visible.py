from __future__ import annotations

from napari_metadata.viewer_widgets._scale_bar import ScaleBarVisible


class _DummyScaleBar:
    def __init__(self, *, visible: bool) -> None:
        self.visible = visible


class _DummyViewer:
    def __init__(self, *, visible: bool) -> None:
        self.scale_bar = _DummyScaleBar(visible=visible)


class TestScaleBarVisible:
    def test_load_entries_reflects_viewer_scale_bar_visibility(
        self, parent_widget
    ):
        viewer = _DummyViewer(visible=True)
        component = ScaleBarVisible(viewer, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].isChecked() is True

    def test_load_entries_applies_tooltip_to_toggle(self, parent_widget):
        viewer = _DummyViewer(visible=False)
        component = ScaleBarVisible(viewer, parent_widget)

        component.load_entries()

        assert (
            component.value_widgets[0].toolTip()
            == 'Show or hide the viewer scale bar overlay.'
        )

    def test_toggle_writes_back_to_viewer(self, parent_widget):
        viewer = _DummyViewer(visible=False)
        component = ScaleBarVisible(viewer, parent_widget)
        component.load_entries()

        component.value_widgets[0].setChecked(True)

        assert viewer.scale_bar.visible is True

    def test_clear_turns_toggle_off(self, parent_widget):
        viewer = _DummyViewer(visible=True)
        component = ScaleBarVisible(viewer, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].isChecked() is False
