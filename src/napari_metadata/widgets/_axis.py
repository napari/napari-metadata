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

from typing import TYPE_CHECKING

import pint
from napari.utils.notifications import show_error
from qtpy.QtCore import QSignalBlocker, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QWidget,
)

from napari_metadata.layer_utils import (
    get_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    get_layer_dimensions,
    resolve_layer,
    set_axes_labels,
    set_axes_scales,
    set_axes_translations,
    set_axes_units,
)
from napari_metadata.units import AxisUnitEnum
from napari_metadata.widgets._base import AxisComponentBase, LayoutEntry

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.layers import Layer
    from napari.viewer import ViewerModel


class AxisLabels(AxisComponentBase):
    """Per-axis label editor using ``QLineEdit`` widgets.

    Unlike the other axis components, ``AxisLabels`` shows the axis
    *index* (-3, -2, -1...) in its name label column, because *it* is the
    widget that edits the axis names.

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
        viewer: ViewerModel,
        main_widget: QWidget,
        *,
        on_labels_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(viewer, main_widget)
        self._on_labels_changed = on_labels_changed
        self._line_edits: list[QLineEdit] = []

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [*super()._all_widget_lists(), self._line_edits]

    def _create_widgets(self, layer: Layer) -> None:
        labels = get_axes_labels(self._napari_viewer, layer)
        ndim = get_layer_dimensions(layer)
        if ndim == 0:
            return
        for i in range(ndim):
            # Index label (not the axis name)
            index_label = QLabel(str(i))
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._axis_name_labels.append(index_label)

            line_edit = QLineEdit()
            line_edit.setText(labels[i] if i < len(labels) else '')
            line_edit.editingFinished.connect(self._on_editing_finished)
            self._line_edits.append(line_edit)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        labels = get_axes_labels(self._napari_viewer, layer)
        for i, label in enumerate(labels):
            if i < len(self._line_edits):
                with QSignalBlocker(self._line_edits[i]):
                    self._line_edits[i].setText(label)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._line_edits[axis_index]])]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return get_axes_labels(self._napari_viewer, layer)

    def _apply_values(self, values: list) -> None:
        set_axes_labels(self._napari_viewer, tuple(values))

    def update_axis_name_labels(self) -> None:
        """No-op: AxisLabels shows indices, not axis names."""

    def get_line_edit_values(self) -> tuple[str, ...]:
        """Return current text from all label line-edits."""
        return tuple(le.text() for le in self._line_edits)

    def _on_editing_finished(self) -> None:
        """Handle editingFinished from any label QLineEdit."""
        labels = self.get_line_edit_values()
        set_axes_labels(self._napari_viewer, labels, self._selected_layer)
        if self._on_labels_changed is not None:
            self._on_labels_changed()


class AxisTranslations(AxisComponentBase):
    """Per-axis translation editor using ``QDoubleSpinBox`` widgets."""

    _label_text = 'Translate:'

    def __init__(self, viewer: ViewerModel, main_widget: QWidget) -> None:
        super().__init__(viewer, main_widget)
        self._spinboxes: list[QDoubleSpinBox] = []

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [*super()._all_widget_lists(), self._spinboxes]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        translations = get_axes_translations(self._napari_viewer, layer)
        ndim = get_layer_dimensions(layer)
        if ndim == 0:
            return
        for value in translations:
            sb = QDoubleSpinBox()
            sb.setDecimals(1)
            sb.setSingleStep(1.0)
            sb.setRange(-1_000_000, 1_000_000)
            sb.setValue(value)
            sb.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(sb)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        translations = get_axes_translations(self._napari_viewer, layer)
        for i, value in enumerate(translations):
            if i < len(self._spinboxes):
                with QSignalBlocker(self._spinboxes[i]):
                    self._spinboxes[i].setValue(value)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._spinboxes[axis_index]])]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return get_axes_translations(self._napari_viewer, layer)

    def _apply_values(self, values: list) -> None:
        set_axes_translations(self._napari_viewer, tuple(values))

    def _on_value_changed(self) -> None:
        values = tuple(sb.value() for sb in self._spinboxes)
        set_axes_translations(
            self._napari_viewer, values, self._selected_layer
        )


class AxisScales(AxisComponentBase):
    """Per-axis scale editor using ``QDoubleSpinBox`` widgets.

    After the user changes a value, the spinbox display is updated to
    reflect the clamped value (``set_axes_scales`` enforces >= 0.001).
    """

    _label_text = 'Scale:'

    def __init__(self, viewer: ViewerModel, main_widget: QWidget) -> None:
        super().__init__(viewer, main_widget)
        self._spinboxes: list[QDoubleSpinBox] = []

    # -- AxisComponentBase overrides ----------------------------------------

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [*super()._all_widget_lists(), self._spinboxes]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        scales = get_axes_scales(self._napari_viewer, layer)
        ndim = get_layer_dimensions(layer)
        if ndim == 0:
            return
        for value in scales:
            sb = QDoubleSpinBox()
            sb.setDecimals(3)
            sb.setSingleStep(0.1)
            sb.setRange(0, 1_000_000)
            sb.setValue(value)
            sb.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(sb)

        self._create_inherit_checkboxes(layer)
        self._selected_layer = layer

    def _refresh_values(self, layer: Layer) -> None:
        scales = get_axes_scales(self._napari_viewer, layer)
        for i, value in enumerate(scales):
            if i < len(self._spinboxes):
                with QSignalBlocker(self._spinboxes[i]):
                    self._spinboxes[i].setValue(value)

    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        return [LayoutEntry(widgets=[self._spinboxes[axis_index]])]

    def _get_layer_values(self, layer: Layer) -> tuple:
        return get_axes_scales(self._napari_viewer, layer)

    def _apply_values(self, values: list) -> None:
        set_axes_scales(self._napari_viewer, tuple(values))

    def _on_value_changed(self) -> None:
        values = tuple(sb.value() for sb in self._spinboxes)
        # set_axes_scales clamps each axis to >= 0.001.
        set_axes_scales(self._napari_viewer, values, self._selected_layer)
        # Reflect the clamped values back in the spinboxes so the user
        for sb in self._spinboxes:
            clamped = max(sb.value(), 0.001)
            if sb.value() != clamped:
                with QSignalBlocker(sb):
                    sb.setValue(clamped)


class AxisUnits(AxisComponentBase):
    """Per-axis unit editor (type ``QComboBox`` + unit ``QComboBox`` / ``QLineEdit``).

    Each axis has three widgets:

    * **type combobox** - selects ``AxisUnitEnum`` (space / time / string)
    * **unit combobox** - shown for space/time; curated list of pint units
    * **unit line-edit** - shown for string type; free-form text
    """

    _label_text = 'Units:'

    def __init__(self, viewer: ViewerModel, main_widget: QWidget) -> None:
        super().__init__(viewer, main_widget)
        self._type_comboboxes: list[QComboBox] = []
        self._unit_comboboxes: list[QComboBox] = []
        self._unit_line_edits: list[QLineEdit] = []

    def _all_widget_lists(self) -> list[list[QWidget]]:
        return [
            *super()._all_widget_lists(),
            self._type_comboboxes,
            self._unit_comboboxes,
            self._unit_line_edits,
        ]

    def _create_widgets(self, layer: Layer) -> None:
        self._create_axis_name_labels(layer)
        layer_units = get_axes_units(self._napari_viewer, layer)
        ndim = get_layer_dimensions(layer)
        if ndim == 0:
            return

        for i in range(ndim):
            unit_str = str(layer_units[i]) if i < len(layer_units) else ''

            # Type combobox (space / time / string)
            type_cb = QComboBox()
            for axis_type in AxisUnitEnum:
                type_cb.addItem(str(axis_type), axis_type)

            # Unit combobox (curated pint units)
            unit_cb = QComboBox()
            matched_type = self._populate_unit_combobox(unit_str, unit_cb)
            type_index = type_cb.findData(
                matched_type
                if matched_type is not None
                else AxisUnitEnum.STRING
            )
            type_cb.setCurrentIndex(type_index)

            # Free-form line edit for STRING type
            line_edit = QLineEdit()

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
        layer_units = get_axes_units(self._napari_viewer, layer)
        for i, unit in enumerate(layer_units):
            if i >= len(self._unit_comboboxes):
                break
            unit_str = str(unit)
            # Determine which AxisUnitEnum this unit belongs to.
            matched_type = AxisUnitEnum.STRING
            for at in AxisUnitEnum:
                cfg = at.value
                if cfg is not None and unit_str in cfg.units:
                    matched_type = at
                    break

            with QSignalBlocker(self._unit_comboboxes[i]):
                self._unit_comboboxes[i].clear()
                cfg = matched_type.value
                if cfg is not None:
                    self._unit_comboboxes[i].addItems(cfg.units)
                    self._unit_comboboxes[i].setCurrentIndex(
                        self._unit_comboboxes[i].findText(unit_str)
                    )
                else:
                    for at in AxisUnitEnum:
                        at_cfg = at.value
                        if at_cfg is not None:
                            self._unit_comboboxes[i].addItems(at_cfg.units)
                    self._unit_comboboxes[i].setCurrentIndex(
                        self._unit_comboboxes[i].findText(
                            AxisUnitEnum.SPACE.value.default
                        )
                    )
            with QSignalBlocker(self._type_comboboxes[i]):
                self._type_comboboxes[i].setCurrentIndex(
                    self._type_comboboxes[i].findText(str(matched_type))
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
        return get_axes_units(self._napari_viewer, layer)

    def _apply_values(self, values: list) -> None:
        set_axes_units(self._napari_viewer, tuple(values))

    @staticmethod
    def _populate_unit_combobox(
        unit_str: str | None, combobox: QComboBox
    ) -> AxisUnitEnum | None:
        """Fill *combobox* with pint units and return the matched enum type."""
        with QSignalBlocker(combobox):
            combobox.clear()

        all_pint_units: list[pint.Unit] = []
        found_type: AxisUnitEnum | None = None
        for axis_type in AxisUnitEnum:
            cfg = axis_type.value
            if cfg is None:
                continue
            all_pint_units.extend(cfg.pint_units())
            if unit_str is not None and unit_str in cfg.units:
                found_type = axis_type

        if found_type is not None:
            chosen_cfg = found_type.value
            if chosen_cfg is None:
                return AxisUnitEnum.STRING
            pint_units = chosen_cfg.pint_units()
        else:
            pint_units = all_pint_units

        ureg = pint.get_application_registry()
        with QSignalBlocker(combobox):
            for pu in pint_units:
                combobox.addItem(str(pu), pu)
            if found_type is None:
                combobox.setCurrentIndex(0)
            else:
                target = ureg.Unit(unit_str)
                idx = combobox.findText(str(target))
                combobox.setCurrentIndex(idx)

        return found_type

    def _sync_visibilities(self) -> None:
        """Toggle unit combobox / line-edit visibility per axis type."""
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentData()
            show_combobox = (
                isinstance(axis_type, AxisUnitEnum)
                and axis_type != AxisUnitEnum.STRING
            )
            self._unit_comboboxes[i].setVisible(show_combobox)
            self._unit_line_edits[i].setVisible(not show_combobox)

    def _sync_line_edit_texts(self) -> None:
        """Update free-form line-edit texts from layer units."""
        current_units = get_axes_units(
            self._napari_viewer, resolve_layer(self._napari_viewer)
        )
        for i in range(min(len(self._unit_line_edits), len(current_units))):
            with QSignalBlocker(self._unit_line_edits[i]):
                self._unit_line_edits[i].setText(str(current_units[i]))

    def _write_units_to_layer(self) -> None:
        """Collect current unit selections and apply to the layer."""
        units: list[str | None] = []
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentData()
            if axis_type is None or axis_type == AxisUnitEnum.STRING:
                text = self._unit_line_edits[i].text().strip()
                if text.lower() == 'none' or not text:
                    units.append(None)
                else:
                    units.append(text)
            else:
                text = self._unit_comboboxes[i].currentText().strip()
                if text.lower() == 'none' or not text:
                    units.append(None)
                else:
                    units.append(text)
        try:
            set_axes_units(self._napari_viewer, tuple(units))
        except (AttributeError, ValueError):
            show_error(f'The layer units {units} has no pint.Unit equivalents')
        self._sync_line_edit_texts()

    def _on_type_changed(self) -> None:
        """Repopulate unit comboboxes when a type combobox changes."""
        current_units = get_axes_units(
            self._napari_viewer, resolve_layer(self._napari_viewer)
        )
        for i in range(len(self._type_comboboxes)):
            axis_type = self._type_comboboxes[i].currentData()
            if not isinstance(axis_type, AxisUnitEnum):
                continue
            cfg = axis_type.value
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

    def __init__(self, viewer: ViewerModel, main_widget: QWidget) -> None:
        self._labels = AxisLabels(
            viewer,
            main_widget,
            on_labels_changed=self._on_labels_changed,
        )
        self._translations = AxisTranslations(viewer, main_widget)
        self._scales = AxisScales(viewer, main_widget)
        self._units = AxisUnits(viewer, main_widget)

        self._components: list[AxisComponentBase] = [
            self._labels,
            self._translations,
            self._scales,
            self._units,
        ]

        self.set_checkboxes_visible(False)

    @property
    def components(self) -> list[AxisComponentBase]:
        """All axis components in display order."""
        return list(self._components)

    def set_checkboxes_visible(self, visible: bool) -> None:
        """Show or hide inheritance checkboxes on all components."""
        for c in self._components:
            c.set_checkboxes_visible(visible)

    def _on_labels_changed(self) -> None:
        """Propagate axis-label text changes to all sibling components."""
        for c in self._components:
            c.update_axis_name_labels()
