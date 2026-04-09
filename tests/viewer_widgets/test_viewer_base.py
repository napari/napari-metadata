from __future__ import annotations

from qtpy.QtWidgets import QLineEdit, QPushButton

from napari_metadata.viewer_widgets._base import ViewerComponentBase


class _DummyViewerComponent(ViewerComponentBase):
    _label_text = 'Viewer Test:'
    _tooltip_text = 'Viewer tooltip.'

    def __init__(self, viewer_model, parent_widget) -> None:
        super().__init__(viewer_model, parent_widget)
        self.get_text_calls = 0

    def _get_display_text(self) -> str:
        self.get_text_calls += 1
        return str(self._napari_viewer.dims.ndim)


class _DummyViewerMultiWidgetComponent(ViewerComponentBase):
    _label_text = 'Viewer Custom:'
    _tooltip_text = 'Custom viewer tooltip.'

    def __init__(self, viewer_model, parent_widget) -> None:
        super().__init__(viewer_model, parent_widget)
        self._line_edit = QLineEdit(parent=parent_widget)
        self._button = QPushButton('Apply', parent=parent_widget)

    @property
    def value_widgets(self) -> list:
        return [self._line_edit, self._button]

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.dims.ndim)

    def _update_display(self) -> None:
        self._line_edit.setText(self._get_display_text())
        self._button.setText(f'Apply {self._napari_viewer.dims.ndim}')


class TestViewerComponentBase:
    def test_load_entries_updates_display_and_tooltip(
        self, viewer_model, parent_widget
    ):
        component = _DummyViewerComponent(viewer_model, parent_widget)

        component.load_entries()

        assert component.value_widgets[0].text() == str(viewer_model.dims.ndim)
        assert component.value_widgets[0].toolTip() == 'Viewer tooltip.'
        assert component.get_text_calls == 1

    def test_default_value_widgets_contains_display_label(
        self, viewer_model, parent_widget
    ):
        component = _DummyViewerComponent(viewer_model, parent_widget)

        assert component.value_widgets == [component._display_label]

    def test_load_entries_tooltip_on_multiple_value_widgets(
        self, viewer_model, parent_widget
    ):
        component = _DummyViewerMultiWidgetComponent(
            viewer_model, parent_widget
        )

        component.load_entries()

        assert component.value_widgets[0].toolTip() == 'Custom viewer tooltip.'
        assert component.value_widgets[1].toolTip() == 'Custom viewer tooltip.'
        assert component.value_widgets[0].text() == str(viewer_model.dims.ndim)
        assert component.value_widgets[1].text() == (
            f'Apply {viewer_model.dims.ndim}'
        )

    def test_clear_resets_default_display(self, viewer_model, parent_widget):
        component = _DummyViewerComponent(viewer_model, parent_widget)
        component.load_entries()

        component.clear()

        assert component.value_widgets[0].text() == ''

    def test_set_visible_toggles_label_and_all_value_widgets(
        self, viewer_model, parent_widget
    ):
        component = _DummyViewerMultiWidgetComponent(
            viewer_model, parent_widget
        )

        component.set_visible(False)
        assert component.component_label.isHidden()
        assert all(widget.isHidden() for widget in component.value_widgets)

        component.set_visible(True)
        assert not component.component_label.isHidden()
        assert all(not widget.isHidden() for widget in component.value_widgets)
