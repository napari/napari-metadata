"""Concrete axis metadata components and the AxisMetadata coordinator.

Each component manages one kind of per-axis data through the
``AxisComponentBase`` template-method API defined in ``_base.py``:

* ``AxisLabels``        - editable axis labels (``QLineEdit``)
* ``AxisTranslations``  - axis translations (``QDoubleSpinBox``)
* ``AxisScales``        - axis scales (``QDoubleSpinBox``)
* ``AxisUnits``         - axis type + unit (``QComboBox`` / ``QLineEdit``)

``AxisMetadata`` is the coordinator that owns all four instances and
provides aggregate operations (label propagation, checkbox toggling).
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

import pint
from napari.utils.notifications import show_warning
from qtpy.QtCore import QSignalBlocker
from qtpy.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QWidget,
)
from superqt import QEnumComboBox

from napari_metadata.units import AxisUnitEnum
from napari_metadata.widgets._base import (
    AxisComponentBase,
    LayoutEntry,
    _ClearableWidgetCollection,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.layers import Layer


class AxisLabels(AxisComponentBase):
    """Per-axis label editor using ``QLineEdit`` widgets.

    Parameters
    ----------
    on_labels_changed : callable, optional
        Callback invoked after labels are written to the layer, so the
        ``AxisMetadata`` coordinator can propagate the new names to
        sibling components.
    """

    _label_text = 'Labels:'

    def __init__(
        self,
        parent_widget: QWidget,
        *,
        on_labels_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent_widget)
        self._on_labels_changed = on_labels_changed
        self._line_edits: list[QLineEdit] = []

    def _all_widget_lists(self) -> list[_ClearableWidgetCollection[QWidget]]:
        return [*super()._all_widget_lists(), self._line_edits]

    def _create_widgets(self, layer: Layer) -> None:
        labels = layer.axis_labels
        ndim = layer.ndim
        for i in range(ndim):
            # Empty label for layout alignment
            empty_label = QLabel(parent=self._parent_widget)
            self._axis_name_labels.append(empty_label)

            line_edit = QLineEdit(parent=self._parent_widget)
            line_edit.setText(labels[i] if i < len(labels) else '')
            line_edit.editingFinished.connect(self._on_editing_finished)
            self._line_edits.append(line_edit)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        labels = layer.axis_labels
        for i, label in enumerate(labels):
            if i < len(self._line_edits):
                with QSignalBlocker(self._line_edits[i]):
                    self._line_edits[i].setText(label)

    def get_layout_entries(self, axis_index: int) -> list[LayoutEntry]:
        """Skip the empty axis-name column; span the line edit across all value cols."""
        line_edit = self._line_edits[axis_index]
        line_edit.setToolTip(self._tooltip_text)
        return [
            LayoutEntry(widgets=[line_edit], col_span=3),
            LayoutEntry(widgets=[self._inherit_checkboxes[axis_index]]),
        ]

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._line_edits[axis_index]])]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return layer.axis_labels

    def _apply_values(self, layer: Layer, values: list) -> None:
        layer.axis_labels = tuple(values)

    def update_axis_name_labels(self, layer: Layer) -> None:
        """Refresh line edits when axis labels change in the layer."""
        self._refresh_values(layer)

    def get_line_edit_values(self) -> tuple[str, ...]:
        """Return current text from all label line-edits."""
        return tuple(le.text() for le in self._line_edits)

    def _on_editing_finished(self) -> None:
        """Handle editingFinished from any label QLineEdit."""
        if self._selected_layer is None:
            return
        labels = self.get_line_edit_values()
        self._selected_layer.axis_labels = labels
        if self._on_labels_changed is not None:
            self._on_labels_changed()


class AxisTranslations(AxisComponentBase):
    """Per-axis translation editor using ``QDoubleSpinBox`` widgets."""

    _label_text = 'Translate:'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._spinboxes: list[QDoubleSpinBox] = []

    def _all_widget_lists(self) -> list[_ClearableWidgetCollection[QWidget]]:
        return [*super()._all_widget_lists(), self._spinboxes]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        translations = layer.translate
        for value in translations:
            sb = QDoubleSpinBox(parent=self._parent_widget)
            sb.setDecimals(1)
            sb.setSingleStep(1.0)
            sb.setRange(-1_000_000, 1_000_000)
            sb.setValue(value)
            sb.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(sb)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        translations = layer.translate
        for i, value in enumerate(translations):
            if i < len(self._spinboxes):
                with QSignalBlocker(self._spinboxes[i]):
                    self._spinboxes[i].setValue(value)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._spinboxes[axis_index]], col_span=2)]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return tuple(layer.translate)

    def _apply_values(self, layer: Layer, values: list) -> None:
        layer.translate = tuple(values)

    def _on_value_changed(self) -> None:
        if self._selected_layer is None:
            return
        values = tuple(sb.value() for sb in self._spinboxes)
        self._selected_layer.translate = values


class AxisScales(AxisComponentBase):
    """Per-axis scale editor using ``QDoubleSpinBox`` widgets.

    The spinbox range enforces a lower bound of ``0.001``.  Live updates
    are pushed while typing; the displayed value syncs back to the layer
    model when editing is committed.
    """

    _SCALE_MINIMUM = 0.0001

    _label_text = 'Scale:'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._spinboxes: list[QDoubleSpinBox] = []

    # -- AxisComponentBase overrides ----------------------------------------

    def _all_widget_lists(self) -> list[_ClearableWidgetCollection[QWidget]]:
        return [*super()._all_widget_lists(), self._spinboxes]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        scales = layer.scale
        for value in scales:
            sb = QDoubleSpinBox(parent=self._parent_widget)
            sb.setDecimals(3)
            sb.setSingleStep(0.1)
            sb.setRange(self._SCALE_MINIMUM, 1_000_000)
            sb.setValue(value)
            sb.valueChanged.connect(self._on_value_changed)
            sb.editingFinished.connect(self._on_editing_finished)
            self._spinboxes.append(sb)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        scales = layer.scale
        for i, value in enumerate(scales):
            if i < len(self._spinboxes):
                with QSignalBlocker(self._spinboxes[i]):
                    self._spinboxes[i].setValue(value)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._spinboxes[axis_index]], col_span=2)]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return tuple(layer.scale)

    def _apply_values(self, layer: Layer, values: list) -> None:
        layer.scale = tuple(max(v, self._SCALE_MINIMUM) for v in values)

    def _on_value_changed(self) -> None:
        if self._selected_layer is None:
            return
        values = tuple(sb.value() for sb in self._spinboxes)
        self._selected_layer.scale = values

    def _on_editing_finished(self) -> None:
        """Sync displayed values to the layer values after edit commit."""
        if self._selected_layer is None:
            return
        scales = self._selected_layer.scale
        for i, value in enumerate(scales):
            if i < len(self._spinboxes):
                with QSignalBlocker(self._spinboxes[i]):
                    self._spinboxes[i].setValue(value)


class AxisUnits(AxisComponentBase):
    """Per-axis unit editor (type ``QComboBox`` + unit ``QComboBox`` / ``QLineEdit``).

    Each axis has three widgets:

    * **type combobox** - selects ``AxisUnitEnum`` (space / time / custom)
    * **unit combobox** - shown for space/time; curated list of pint units
    * **unit line-edit** - shown for custom type; any pint-parseable unit
    """

    _label_text = 'Units:'
    _tooltip_text = 'The Pint unit associated with each axis.'

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._type_comboboxes: list[QEnumComboBox] = []
        self._unit_comboboxes: list[QComboBox] = []
        self._unit_line_edits: list[QLineEdit] = []

    def _all_widget_lists(self) -> list[_ClearableWidgetCollection[QWidget]]:
        return [
            *super()._all_widget_lists(),
            self._type_comboboxes,
            self._unit_comboboxes,
            self._unit_line_edits,
        ]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        layer_units = layer.units
        ndim = layer.ndim

        for i in range(ndim):
            unit_str = str(layer_units[i]) if i < len(layer_units) else ''

            # Type combobox (space / time / custom)
            type_cb = QEnumComboBox(
                parent=self._parent_widget, enum_class=AxisUnitEnum
            )

            # Unit combobox (curated pint units)
            unit_cb = QComboBox(parent=self._parent_widget)
            matched_type = self._populate_unit_combobox(unit_str, unit_cb)
            type_cb.setCurrentEnum(
                matched_type
                if matched_type is not None
                else AxisUnitEnum.CUSTOM
            )

            # Free-form line edit for CUSTOM type
            line_edit = QLineEdit(parent=self._parent_widget)

            self._type_comboboxes.append(type_cb)
            self._unit_comboboxes.append(unit_cb)
            self._unit_line_edits.append(line_edit)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

        # Connect signals *after* all widgets exist to avoid partial updates.
        for type_cb in self._type_comboboxes:
            type_cb.currentIndexChanged.connect(self._on_type_changed)
        for unit_cb in self._unit_comboboxes:
            unit_cb.currentIndexChanged.connect(self._on_unit_changed)
        for le in self._unit_line_edits:
            le.editingFinished.connect(self._on_unit_changed)

        self._sync_visibilities()
        self._sync_line_edit_texts()

    def _refresh_values(self, layer: Layer) -> None:
        layer_units = layer.units
        for i, unit in enumerate(layer_units[: len(self._unit_comboboxes)]):
            unit_str = str(unit)
            matched_type = self._populate_unit_combobox(
                unit_str, self._unit_comboboxes[i]
            )
            with QSignalBlocker(self._unit_line_edits[i]):
                self._unit_line_edits[i].setText(unit_str)
            with QSignalBlocker(self._type_comboboxes[i]):
                self._type_comboboxes[i].setCurrentEnum(
                    matched_type or AxisUnitEnum.CUSTOM
                )
        self._sync_line_edit_texts()
        self._sync_visibilities()

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [
            LayoutEntry(widgets=[self._type_comboboxes[axis_index]]),
            LayoutEntry(
                widgets=[
                    self._unit_comboboxes[axis_index],
                    self._unit_line_edits[axis_index],
                ]
            ),
        ]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return layer.units

    def _apply_values(self, layer: Layer, values: list) -> None:
        layer.units = tuple(values)

    @staticmethod
    def _populate_unit_combobox(
        unit_str: str | None, combobox: QComboBox
    ) -> AxisUnitEnum | None:
        """Fill *combobox* with pint units and return the matched enum type."""
        with QSignalBlocker(combobox):
            combobox.clear()

        for axis_type in AxisUnitEnum:
            cfg = axis_type.config
            if cfg is None:
                continue
            if unit_str is not None and unit_str in cfg.units:
                ureg = pint.get_application_registry()
                with QSignalBlocker(combobox):
                    for pu in cfg.pint_units():
                        combobox.addItem(str(pu), pu)
                target = ureg.Unit(unit_str)
                idx = combobox.findText(str(target))
                combobox.setCurrentIndex(idx)
                return axis_type

        return None

    def _sync_visibilities(self) -> None:
        """Toggle unit combobox / line-edit visibility per axis type."""
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentEnum()
            show_combobox = axis_type != AxisUnitEnum.CUSTOM
            self._unit_comboboxes[i].setVisible(show_combobox)
            self._unit_line_edits[i].setVisible(not show_combobox)

    def _sync_line_edit_texts(self) -> None:
        """Update free-form line-edit texts from layer units."""
        if self._selected_layer is None:
            return
        current_units = self._selected_layer.units
        for i in range(min(len(self._unit_line_edits), len(current_units))):
            with QSignalBlocker(self._unit_line_edits[i]):
                self._unit_line_edits[i].setText(str(current_units[i]))

    @staticmethod
    def _normalize_widget_unit_text(text: str) -> str:
        """Map empty or explicit reset text to napari's pixel default."""
        normalized = text.strip()
        return (
            'pixel'
            if not normalized or normalized.lower() == 'none'
            else normalized
        )

    def _write_units_to_layer(self) -> None:
        """Collect current unit selections and apply to the layer."""
        if self._selected_layer is None:
            return
        units: list[str] = []
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentEnum()
            if axis_type == AxisUnitEnum.CUSTOM:
                units.append(
                    self._normalize_widget_unit_text(
                        self._unit_line_edits[i].text()
                    )
                )
            else:
                units.append(
                    self._normalize_widget_unit_text(
                        self._unit_comboboxes[i].currentText()
                    )
                )
        try:
            self._selected_layer.units = tuple(units)
        except (AttributeError, ValueError) as e:
            show_warning(str(e))
        self._sync_line_edit_texts()

    def _on_type_changed(self) -> None:
        """Repopulate unit comboboxes when a type combobox changes."""
        if self._selected_layer is None:
            return
        current_units = self._selected_layer.units
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentEnum()
            cfg = axis_type.config
            current_unit_str = (
                str(current_units[i]) if i < len(current_units) else ''
            )
            with QSignalBlocker(self._unit_comboboxes[i]):
                self._unit_comboboxes[i].clear()
                if cfg is not None:
                    for unit in cfg.pint_units():
                        self._unit_comboboxes[i].addItem(str(unit), unit)
                idx = self._unit_comboboxes[i].findText(current_unit_str)
                if idx == -1 and cfg is not None:
                    idx = self._unit_comboboxes[i].findText(cfg.default)
                self._unit_comboboxes[i].setCurrentIndex(idx)
        self._write_units_to_layer()
        self._sync_visibilities()

    def _on_unit_changed(self) -> None:
        """Handle unit combobox selection or line-edit change."""
        self._write_units_to_layer()
        self._sync_visibilities()


class AxisMetadata:
    """Coordinator that owns all four axis component instances.

    Provides aggregate operations consumed by ``MetadataWidget``:
    * Iterate over ``components``
    * Propagate axis-label changes across components
    * Toggle inheritance checkboxes globally
    """

    def __init__(self, parent_widget: QWidget) -> None:
        self._labels = AxisLabels(
            parent_widget,
            on_labels_changed=self._on_labels_changed,
        )
        self._translations = AxisTranslations(parent_widget)
        self._scales = AxisScales(parent_widget)
        self._units = AxisUnits(parent_widget)

        self._components: list[AxisComponentBase] = [
            self._labels,
            self._translations,
            self._scales,
            self._units,
        ]
        self._selected_layer: Layer | None = None

        self.set_checkboxes_visible(False)

    @property
    def components(self) -> list[AxisComponentBase]:
        """All axis components in display order."""
        return list(self._components)

    def connect_layer_events(self, layer: Layer) -> None:
        """Subscribe to *layer* events that require widget refresh."""
        self._selected_layer = layer
        layer.events.axis_labels.connect(self._on_labels_changed)
        layer.events.scale.connect(self._on_scale_changed)
        layer.events.translate.connect(self._on_translate_changed)
        layer.events.units.connect(self._on_units_changed)

    def disconnect_layer_events(self, layer: Layer) -> None:
        """Unsubscribe from *layer* events."""
        self._selected_layer = None
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.axis_labels.disconnect(self._on_labels_changed)
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.scale.disconnect(self._on_scale_changed)
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.translate.disconnect(self._on_translate_changed)
        with suppress(TypeError, ValueError, RuntimeError):
            layer.events.units.disconnect(self._on_units_changed)

    def _on_scale_changed(self) -> None:
        if self._selected_layer is not None:
            self._scales._refresh_values(self._selected_layer)

    def _on_translate_changed(self) -> None:
        if self._selected_layer is not None:
            self._translations._refresh_values(self._selected_layer)

    def _on_units_changed(self) -> None:
        if self._selected_layer is not None:
            self._units._refresh_values(self._selected_layer)

    def set_checkboxes_visible(self, visible: bool) -> None:
        """Show or hide inheritance checkboxes on all components."""
        for c in self._components:
            c.set_checkboxes_visible(visible)

    def _on_labels_changed(self) -> None:
        """Propagate axis-label text changes to all sibling components."""
        if self._selected_layer is None:
            return
        for c in self._components:
            c.update_axis_name_labels(self._selected_layer)
