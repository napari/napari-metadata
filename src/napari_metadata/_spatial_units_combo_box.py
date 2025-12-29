from typing import TYPE_CHECKING

from pint import Unit, UnitRegistry
from qtpy.QtWidgets import QComboBox

from napari_metadata._model import coerce_extra_metadata
from napari_metadata._space_units import SpaceUnits

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


class SpatialUnitsComboBox(QComboBox):
    def __init__(self, viewer: 'ViewerModel') -> None:
        super().__init__()
        self._viewer = viewer
        self.addItems(SpaceUnits.names())
        self._unit_registry: UnitRegistry = UnitRegistry()
        self._PINT_TO_SPACE_UNIT: dict[Unit, SpaceUnits] = {
            self._unit_registry.nanometer: SpaceUnits.NANOMETER,
            self._unit_registry.micron: SpaceUnits.MICROMETER,
            self._unit_registry.micrometer: SpaceUnits.MICROMETER,
            self._unit_registry.millimeter: SpaceUnits.MILLIMETER,
            self._unit_registry.centimeter: SpaceUnits.CENTIMETER,
            self._unit_registry.meter: SpaceUnits.METER,
        }

        self._viewer.scale_bar.events.unit.connect(
            self._on_viewer_scale_bar_unit_changed
        )
        self.currentTextChanged.connect(self._on_units_changed)

        self._on_units_changed()

    def set_selected_layer(self, layer: 'Layer') -> None:
        extras = coerce_extra_metadata(self._viewer, layer)
        unit = extras.get_space_unit()
        self._viewer.scale_bar.unit = (
            str(unit) if unit != SpaceUnits.NONE else None
        )

    def _on_units_changed(self) -> None:
        text = self.currentText()
        unit = None if text == 'none' else text
        self._viewer.scale_bar.unit = unit

    def _on_viewer_scale_bar_unit_changed(self, event) -> None:
        unit = event.value
        text = 'none' if unit is None else self._convert_model_unit(unit)
        self.setCurrentText(text)

    def _convert_model_unit(self, model_unit: str) -> str:
        quantity = self._unit_registry(model_unit)
        if quantity is None:
            return 'none'
        unit = quantity.units
        if unit not in self._PINT_TO_SPACE_UNIT:
            return 'none'
        return str(self._PINT_TO_SPACE_UNIT[unit])
