from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING

from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.components._viewer_constants import CanvasPosition
from qtpy.QtCore import QSignalBlocker, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt import QDoubleSlider, QEnumComboBox, QToggleSwitch

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
        unit = self._napari_viewer.scale_bar.unit
        index = self._unit_combobox.findData(unit)
        with QSignalBlocker(self._unit_combobox):
            self._unit_combobox.setCurrentIndex(index if index >= 0 else 0)

    def _get_display_text(self) -> str:
        return self._unit_combobox.currentText()

    def _on_unit_changed(self) -> None:
        self._napari_viewer.scale_bar.unit = self._unit_combobox.currentData()


class ScaleBarFontSize(ViewerComponentBase):
    """Scale bar component to set the font size of the units"""

    _label_text = 'Font size:'
    _tooltip_text = 'Font size of the units text displayed on the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._font_size_spinbox = QDoubleSpinBox(parent=parent_widget)
        self._font_size_spinbox.setRange(0.0000001, 100)
        self._font_size_spinbox.setSingleStep(1)
        self._font_size_spinbox.setDecimals(0)
        self._font_size_spinbox.setValue(10)
        self._font_size_spinbox.valueChanged.connect(self._on_value_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._font_size_spinbox]

    def clear(self) -> None:
        self._font_size_spinbox.setValue(10)

    def _update_display(self) -> None:
        return

    def _get_display_text(self) -> str:
        return str(self._font_size_spinbox.value())

    def _on_value_changed(self) -> None:
        self._napari_viewer.scale_bar.font_size = (
            self._font_size_spinbox.value()
        )


class ScaleBarFixedLength(ViewerComponentBase):
    """Scale bar component to set a fixed length to the scale bar."""

    _label_text = 'Fixed length:'
    _tooltip_text = 'Sets a fixed length to the scale bar. It the button is off, the scale bar length is determined by the zoom level'

    def __init__(
        self, napari_viewer: ViewerModel, parent_widget: QWidget
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._solve_fixed_length)
        self._length_spinbox = QDoubleSpinBox(parent=parent_widget)
        self._length_spinbox.setRange(0, 1000)
        self._length_spinbox.valueChanged.connect(self._solve_fixed_length)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch, self._length_spinbox]

    def clear(self) -> None:
        self._toggle_switch.setChecked(False)
        self._length_spinbox.setValue(0)

    def _update_display(self) -> None:
        return

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.length)

    def _solve_fixed_length(self) -> None:
        self._set_fixed_length(
            self._length_spinbox.value()
        ) if self._toggle_switch.isChecked() else self._set_fixed_length(None)

    def _set_fixed_length(self, value: float | None) -> None:
        self._napari_viewer.scale_bar.length = value


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
        self._syncing_from_viewer = False
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._on_toggled)
        self._color_swatch = QColorSwatchEdit(
            parent=parent_widget, initial_color='magenta'
        )
        self._color_swatch.color_changed.connect(self._on_color_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch, self._color_swatch]

    def clear(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(False)
        finally:
            self._syncing_from_viewer = False
        self._color_swatch.setColor('magenta')

    def _update_display(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(
                self._napari_viewer.scale_bar.colored
            )
        finally:
            self._syncing_from_viewer = False
        self._color_swatch.setColor(self._napari_viewer.scale_bar.color)

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.color)

    def _on_toggled(self, checked: bool) -> None:
        if self._syncing_from_viewer:
            return
        self._napari_viewer.scale_bar.colored = checked

    def _on_color_changed(self, color) -> None:
        self._napari_viewer.scale_bar.color = color


class ScaleBarBox(ViewerComponentBase):
    """Scale bar bomponent to toggle the box of the scale bar and adjust its color"""

    _label_text = 'Box:'
    _tooltip_text = 'Toggle the box of the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._syncing_from_viewer = False
        self._toggle_switch = QToggleSwitch(parent=parent_widget)
        self._toggle_switch.toggled.connect(self._on_toggled)
        self._color_swatch = QColorSwatchEdit(
            parent=parent_widget, initial_color='green'
        )
        self._color_swatch.color_changed.connect(self._on_color_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._toggle_switch, self._color_swatch]

    def clear(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(False)
        finally:
            self._syncing_from_viewer = False

    def _update_display(self) -> None:
        self._syncing_from_viewer = True
        try:
            self._toggle_switch.setChecked(self._napari_viewer.scale_bar.box)
        finally:
            self._syncing_from_viewer = False
        if self._napari_viewer.scale_bar.box_color is not None:
            self._color_swatch.setColor(
                self._napari_viewer.scale_bar.box_color
            )

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.box)

    def _on_toggled(self, checked: bool) -> None:
        if self._syncing_from_viewer:
            return
        self._napari_viewer.scale_bar.box = checked
        if checked and self._napari_viewer.scale_bar.box_color is None:
            self._napari_viewer.scale_bar.box_color = self._color_swatch.color

    def _on_color_changed(self, color) -> None:
        self._napari_viewer.scale_bar.box_color = color


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


class ScaleBarOpacity(ViewerComponentBase):
    _label_text = 'Opacity:'
    _tooltip_text = 'Set the opacity of the scale bar.'

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._slider = QDoubleSlider(parent=parent_widget)
        self._slider.setOrientation(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1)
        self._slider.setValue(1.0)
        self._slider.setSingleStep(0.01)
        self._slider.valueChanged.connect(self._opacity_changed)
        self._spin_box = QDoubleSpinBox(parent=parent_widget)
        self._spin_box.setRange(0, 1)
        self._spin_box.setValue(1.0)
        self._spin_box.setSingleStep(0.01)
        self._spin_box.valueChanged.connect(self._opacity_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._slider, self._spin_box]

    def clear(self) -> None:
        self._slider.setValue(1)
        self._spin_box.setValue(1)

    def _update_display(self) -> None:
        return

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.opacity)

    def _opacity_changed(self, value: float) -> None:
        if self._slider.value() != value:
            with QSignalBlocker(self._slider):
                self._slider.setValue(value)
        if self._spin_box.value() != value:
            with QSignalBlocker(self._spin_box):
                self._spin_box.setValue(value)
        self._napari_viewer.scale_bar.opacity = value


class ScaleBarPosition(ViewerComponentBase):
    """Component that controls the scale bar position."""

    _label_text = 'Position:'
    _tooltip_text = 'Set the position of the scale bar.'

    def __init__(
        self, napari_viewer: ViewerModel, parent_widget: QWidget
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._position_combobox = QEnumComboBox(
            parent=parent_widget,
            enum_class=CanvasPosition,
        )
        self._position_combobox.currentIndexChanged.connect(
            self._on_position_changed
        )

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._position_combobox]

    def clear(self) -> None:
        self._position_combobox.setCurrentEnum(CanvasPosition.BOTTOM_RIGHT)

    def _update_display(self) -> None:
        with QSignalBlocker(self._position_combobox):
            self._position_combobox.setCurrentEnum(
                self._napari_viewer.scale_bar.position
            )

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.position)

    def _on_position_changed(self) -> None:
        self._napari_viewer.scale_bar.position = (
            self._position_combobox.currentEnum()
        )


class ScaleBarOrder(ViewerComponentBase):
    """Component that controls the scale bar rendering order."""

    _label_text = 'Order:'
    _tooltip_text = 'Rendering order of the scale bar overlay.'

    def __init__(
        self, napari_viewer: ViewerModel, parent_widget: QWidget
    ) -> None:
        super().__init__(napari_viewer, parent_widget)
        self._order_spinbox = QSpinBox(parent=parent_widget)
        self._order_spinbox.setRange(0, 10**9)
        self._order_spinbox.valueChanged.connect(self._on_order_changed)

    @property
    def value_widgets(self) -> list[QWidget]:
        return [self._order_spinbox]

    def clear(self) -> None:
        self._order_spinbox.setValue(10**6)

    def _update_display(self) -> None:
        with QSignalBlocker(self._order_spinbox):
            self._order_spinbox.setValue(self._napari_viewer.scale_bar.order)

    def _get_display_text(self) -> str:
        return str(self._napari_viewer.scale_bar.order)

    def _on_order_changed(self) -> None:
        self._napari_viewer.scale_bar.order = self._order_spinbox.value()


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
        self._scale_bar_font_size = ScaleBarFontSize(
            napari_viewer, parent_widget
        )
        self._scale_bar_fixed_length = ScaleBarFixedLength(
            napari_viewer, parent_widget
        )
        self._scale_bar_color = ScaleBarColor(napari_viewer, parent_widget)
        self._scale_bar_ticks = ScaleBarTicks(napari_viewer, parent_widget)
        self._scale_bar_box = ScaleBarBox(napari_viewer, parent_widget)
        self._scale_bar_opacity = ScaleBarOpacity(napari_viewer, parent_widget)
        self._scale_bar_position = ScaleBarPosition(
            napari_viewer, parent_widget
        )
        self._scale_bar_order = ScaleBarOrder(napari_viewer, parent_widget)
        self._components = (
            list(components)
            if components is not None
            else [
                self._scale_bar_visible,
                self._scale_bar_units,
                self._scale_bar_font_size,
                self._scale_bar_color,
                self._scale_bar_ticks,
                self._scale_bar_box,
                self._scale_bar_fixed_length,
                self._scale_bar_opacity,
                self._scale_bar_position,
                self._scale_bar_order,
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
        self._napari_viewer.scale_bar.events.connect(
            self._on_scale_bar_changed
        )

    def _disconnect_scale_bar_events(self) -> None:
        with suppress(TypeError, ValueError, RuntimeError):
            self._napari_viewer.scale_bar.events.disconnect(
                self._on_scale_bar_changed
            )

    def _on_scale_bar_changed(self, event=None) -> None:
        self.refresh()


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


# TODO:
# We need to connect everything, specially the scale bar colors and the scale bar box colors.
# There is an issue when setting the scale bar length. When it is set, the canvas won't update. This is a scale_bar.events.length issue, not a widget issue. We need to call refresh on something or, preferably, change the behavior on napari. That is strange because the font size does refresh the canvas
