from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from qtpy.QtCore import QSignalBlocker
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from superqt import QToggleSwitch

from napari_metadata.viewer_widgets._base import ViewerComponentBase

if TYPE_CHECKING:
    from napari.components import ViewerModel


class ScaleBarVisible(ViewerComponentBase):
    """Toggle component controlling scale bar visibility."""

    _label_text = 'Visible:'
    _tooltip_text = 'Show or hide the viewer scale bar overlay.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._on_toggled)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch]

    def clear(self) -> None:
        with QSignalBlocker(self._toggle_switch):
            self._toggle_switch.setChecked(False)

    def _update_display(self) -> None:
        with QSignalBlocker(self._toggle_switch):
            self._toggle_switch.setChecked(
                self._napari_viewer.scale_bar.visible
            )

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.visible)

    def _on_toggled(self, checked: bool) -> None:
        self._napari_viewer.scale_bar.visible = checked


class ScaleBarMetadata:
    """Coordinator that owns the scale bar viewer components."""

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
        components: Sequence[ViewerComponentBase] | None = None,
    ) -> None:
        self._napari_viewer = napari_viewer
        self._parent_widget = parent_widget
        self._scale_bar_visible = ScaleBarVisible(napari_viewer, parent_widget)
        self._components = (
            list(components)
            if components is not None
            else [self._scale_bar_visible]
        )

    @property
    def components(self) -> list[ViewerComponentBase]:
        """All scale bar components in display order."""
        return list(self._components)

    def refresh(self) -> None:
        """Refresh all managed components from the current viewer."""
        for component in self._components:
            component.load_entries(self._napari_viewer)


class ScaleBarWidget(QWidget):
    """Scale bar section of the viewer metadata widget."""

    def __init__(
        self,
        napari_viewer: ViewerModel,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self._napari_viewer = napari_viewer
        self._metadata = ScaleBarMetadata(napari_viewer, self)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._rows_layout = QVBoxLayout()
        self._layout.addLayout(self._rows_layout)
        self._populate_rows()
        self._layout.addStretch()

    def _populate_rows(self) -> None:
        for component in self._metadata.components:
            row_layout = QHBoxLayout()
            row_layout.addWidget(component.component_label)
            for widget in component.value_widgets:
                row_layout.addWidget(widget)
            row_layout.addStretch()
            self._rows_layout.addLayout(row_layout)
