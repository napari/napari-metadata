from copy import deepcopy
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    Protocol,
    Tuple,
    Sequence,
    runtime_checkable,
    cast
)

from ._axis_type import AxisType
from ._space_units import SpaceUnits
from ._time_units import TimeUnits

import pint
import numpy as np

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer

def get_axes_labels(viewer: "ViewerModel", layer: "Layer | None" = None) -> Tuple[str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.axis_labels

def set_active_layer_axes_labels(viewer: "ViewerModel", axes_labels: Tuple[str, ...]):
    layer: "Layer | None" = get_active_layer(viewer)
    if layer is None:
        return
    layer.axis_labels = axes_labels

def get_pint_ureg(viewer: "ViewerModel") -> pint.UnitRegistry | None:
    layer: "Layer | None" = get_active_layer(viewer)
    if layer is None:
        return None
    layer_units = layer.units
    for unit in layer_units:
        if isinstance(unit, str):
            continue
        else:
            unit_reg = unit._REGISTRY
            return unit_reg

def get_axes_units(viewer: "ViewerModel", layer: "Layer | None" = None) -> Tuple[pint.Unit | str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.units

def set_active_layer_axes_units(viewer: "ViewerModel", axes_units: Tuple[str, ...]) -> None:
    layer: "Layer | None" = get_active_layer(viewer)
    if layer is None:
        return
    layer.units = axes_units

def get_axes_scales(viewer: "ViewerModel", layer: "Layer | None" = None) -> Tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(Tuple[float, ...], active_layer.scale) 

def set_active_layer_axes_scales(viewer: "ViewerModel", axes_scales: Tuple[float, ...]) -> None:
    layer: "Layer | None" = get_active_layer(viewer)
    if layer is None:
        return
    for scale in axes_scales:
        if not isinstance(scale, float):
            return
        if scale <= 0:
            scale = 0.001
    layer.scale = np.array(axes_scales)

def get_axes_translations(viewer: "ViewerModel", layer: "Layer | None" = None) -> Tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(Tuple[float, ...], active_layer.translate)

def set_active_layer_axes_translations(viewer: "ViewerModel", axes_translations: Tuple[float, ...]) -> None:
    layer: "Layer | None" = get_active_layer(viewer)
    if layer is None:
        return
    layer.translate = axes_translations

def get_layer_data_shape(layer: "Layer | None") -> Tuple[int, ...]:
    if layer is None:
        return ()
    layer_data = layer.data
    if hasattr(layer_data, "shape"):
        return layer_data.shape
    if isinstance(layer_data, Sequence):
        return (len(layer_data),)
    return ()

def get_layer_data_dtype(layer: "Layer | None") -> str:
    if layer is None:
        return ""
    layer_data = layer.data
    if hasattr(layer_data, "dtype"):
        return str(layer_data.dtype)
    if isinstance(layer_data, Sequence) and len(layer_data) > 0 and hasattr(layer_data[0], "dtype"):
        return str(layer_data[0].dtype)
    return "Unknown"

def get_layer_source_path(layer: "Layer | None") -> str:
    if layer is None:
        return ""
    if layer.source.path is None:
        return ""
    return layer.source.path

def get_layer_dimensions(layer: "Layer | None") -> int:
    if layer is None:
        return 0
    return layer.ndim

def get_active_layer(viewer: "ViewerModel") -> "Layer | None":
    return viewer.layers.selection.active



@runtime_checkable
class Axis(Protocol):
    name: str

    def get_type(self) -> AxisType:
        ...

    def get_unit_name(self) -> Optional[str]:
        ...


@dataclass
class SpaceAxis:
    name: str
    unit: SpaceUnits = SpaceUnits.NONE

    def get_type(self) -> AxisType:
        return AxisType.SPACE

    def get_unit_name(self) -> Optional[str]:
        return str(self.unit)


@dataclass
class TimeAxis:
    name: str
    unit: TimeUnits = TimeUnits.NONE

    def get_type(self) -> AxisType:
        return AxisType.TIME

    def get_unit_name(self) -> Optional[str]:
        return str(self.unit)


@dataclass
class ChannelAxis:
    name: str

    def get_type(self) -> AxisType:
        return AxisType.CHANNEL

    def get_unit_name(self) -> Optional[str]:
        return None


EXTRA_METADATA_KEY = "napari-metadata-plugin"


@dataclass(frozen=True)
class OriginalMetadata:
    axes: Tuple[Axis]
    name: Optional[str]
    scale: Optional[Tuple[float, ...]]
    translate: Optional[Tuple[float, ...]]


@dataclass
class ExtraMetadata:
    axes: List[Axis]
    original: Optional[OriginalMetadata] = None

    def get_axis_names(self) -> Tuple[str, ...]:
        return tuple(axis.name for axis in self.axes)

    def set_axis_names(self, names: Tuple[str, ...]) -> None:
        assert len(self.axes) == len(names)
        for axis, name in zip(self.axes, names):
            axis.name = name

    def get_space_unit(self) -> SpaceUnits:
        units = tuple(
            axis.unit for axis in self.axes if isinstance(axis, SpaceAxis)
        )
        return units[0] if len(set(units)) == 1 else SpaceUnits.NONE

    def set_space_unit(self, unit: SpaceUnits) -> None:
        for axis in self.axes:
            if isinstance(axis, SpaceAxis):
                axis.unit = unit

    def get_time_unit(self) -> TimeUnits:
        units = tuple(
            axis.unit for axis in self.axes if isinstance(axis, TimeAxis)
        )
        return units[0] if len(set(units)) == 1 else TimeUnits.NONE

    def set_time_unit(self, unit: TimeUnits) -> None:
        for axis in self.axes:
            if isinstance(axis, TimeAxis):
                axis.unit = unit


def extra_metadata(layer: "Layer") -> Optional[ExtraMetadata]:
    return layer.metadata.get(EXTRA_METADATA_KEY)


def coerce_extra_metadata(
    viewer: "ViewerModel", layer: "Layer"
) -> ExtraMetadata:
    if EXTRA_METADATA_KEY not in layer.metadata:
        axes = [
            SpaceAxis(name=name)
            for name in viewer.dims.axis_labels[-layer.ndim :]  # noqa
        ]
        original = OriginalMetadata(
            axes=tuple(deepcopy(axes)),
            name=layer.name,
            scale=tuple(layer.scale),
            translate=tuple(layer.translate),
        )
        layer.metadata[EXTRA_METADATA_KEY] = ExtraMetadata(
            axes=axes,
            original=original,
        )
    return layer.metadata[EXTRA_METADATA_KEY]


def is_metadata_equal_to_original(layer: Optional["Layer"]) -> bool:
    if layer is None:
        return False
    extras = extra_metadata(layer)
    if extras is None:
        return False
    if extras.original is None:
        return False
    if tuple(extras.axes) != extras.original.axes:
        return False
    if tuple(layer.scale) != extras.original.scale:
        return False
    if tuple(layer.translate) != extras.original.translate:
        return False
    if layer.name != extras.original.name:
        return False
    return True
