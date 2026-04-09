from __future__ import annotations

from napari_metadata.viewer_widgets._base import ViewerComponentBase
from napari_metadata.viewer_widgets._scale_bar import ScaleBarMetadata


class _DummyScaleBarComponent(ViewerComponentBase):
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


class TestScaleBarMetadata:
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
