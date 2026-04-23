from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING

from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from superqt import QToggleSwitch

from napari_metadata.units import AxisUnitEnum
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
        self._syncing_from_viewer = False
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._on_toggled)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch]

    def clear(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(False)
        finally:
            self._syncing_from_viewer = False

    def _update_display(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(
                self._napari_viewer.scale_bar.visible
            )
        finally:
            self._syncing_from_viewer = False

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.visible)

    def _on_toggled(self, checked: bool) -> None:
        if self._syncing_from_viewer:
            return
        self._napari_viewer.scale_bar.visible = checked


class ScaleBarUnits(ViewerComponentBase):
    """Scale bar component to set the units displayed text on the ScaleBarOverlay."""

    _label_text = 'Units: '
    _tooltip_text = 'Units text displayed on the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._unit_combobox = QComboBox(parent=parent_widget)
        config = AxisUnitEnum.SPACE.config
        if config is not None:
            for unit in config.units:
                self._unit_combobox.addItem(unit, unit)
        self._unit_combobox.currentIndexChanged.connect(self._on_unit_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._unit_combobox]

    def clear(self) -> None:
        self._unit_combobox.setCurrentIndex(0)

    def _update_display(self) -> None:
        return

    def _get_display_text(self) -> str:
        return self._unit_combobox.currentText()

    def _on_unit_changed(self) -> None:
        print('Unit changed')
        return


class ScaleBarColor(ViewerComponentBase):
    """Scale bar component to toggle color mode and pick the color"""

    _label_text = 'Custom color:'
    _tooltip_text = 'Color of the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._color_swatch = QColorSwatchEdit(
            parent=parent_widget, initial_color='white'
        )

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch, self._color_swatch]

    def clear(self) -> None:
        self._toggle_switch.setChecked(False)
        self._color_swatch.setColor('white')

    def _update_display(self) -> None:
        return

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.color)

    def _on_toggled(self, checked: bool) -> None:
        self._napari_viewer.scale_bar.colored = checked


class ScaleBarTicks(ViewerComponentBase):
    """Toggle component controlling scale bar ticks visibility."""

    _label_text = 'Ticks:'
    _tooltip_text = 'Show or hide the ticks at the ends of the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._syncing_from_viewer = False
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._on_toggled)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch]

    def clear(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(False)
        finally:
            self._syncing_from_viewer = False

    def _update_display(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(self._napari_viewer.scale_bar.ticks)
        finally:
            self._syncing_from_viewer = False

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.ticks)

    def _on_toggled(self, checked: bool) -> None:
        if self._syncing_from_viewer:
            return
        self._napari_viewer.scale_bar.ticks = checked


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
        self._scale_bar_units = ScaleBarUnits(napari_viewer, parent_widget)
        self._scale_bar_color = ScaleBarColor(napari_viewer, parent_widget)
        self._scale_bar_ticks = ScaleBarTicks(napari_viewer, parent_widget)
        self._components = (
            list(components)
            if components is not None
            else [
                self._scale_bar_visible,
                self._scale_bar_units,
                self._scale_bar_color,
                self._scale_bar_ticks,
            ]
        )
        self._connect_scale_bar_events()

    @property
    def components(self) -> list[ViewerComponentBase]:
        """All scale bar components in display order."""
        return list(self._components)

    def refresh(self) -> None:
        """Refresh all managed components from the current viewer."""
        for component in self._components:
            component.load_entries(self._napari_viewer)

    def _connect_scale_bar_events(self) -> None:
        self._napari_viewer.scale_bar.events.visible.connect(
            self._on_visible_changed
        )

    def _disconnect_scale_bar_events(self) -> None:
        with suppress(TypeError, ValueError, RuntimeError):
            self._napari_viewer.scale_bar.events.visible.disconnect(
                self._on_visible_changed
            )

    def _on_visible_changed(self) -> None:
        self._scale_bar_visible.load_entries(self._napari_viewer)


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
        self._metadata.refresh()
        self._layout.addStretch()

    def _populate_rows(self) -> None:
        for component in self._metadata.components:
            row_layout = QHBoxLayout()
            row_layout.addWidget(component.component_label)
            for widget in component.value_widgets:
                row_layout.addWidget(widget)
            row_layout.addStretch()
            self._rows_layout.addLayout(row_layout)
