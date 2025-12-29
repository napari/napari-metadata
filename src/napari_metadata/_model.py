from copy import deepcopy
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Optional,
    Protocol,
    runtime_checkable,
)

from ._axis_type import AxisType
from ._space_units import SpaceUnits
from ._time_units import TimeUnits

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


@runtime_checkable
class Axis(Protocol):
    name: str

    def get_type(self) -> AxisType: ...

    def get_unit_name(self) -> Optional[str]: ...


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


EXTRA_METADATA_KEY = 'napari-metadata-plugin'


@dataclass(frozen=True)
class OriginalMetadata:
    axes: tuple[Axis]
    name: Optional[str]
    scale: Optional[tuple[float, ...]]
    translate: Optional[tuple[float, ...]]


@dataclass
class ExtraMetadata:
    axes: list[Axis]
    original: Optional[OriginalMetadata] = None

    def get_axis_names(self) -> tuple[str, ...]:
        return tuple(axis.name for axis in self.axes)

    def set_axis_names(self, names: tuple[str, ...]) -> None:
        assert len(self.axes) == len(names)
        for axis, name in zip(self.axes, names, strict=False):
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


def extra_metadata(layer: 'Layer') -> Optional[ExtraMetadata]:
    return layer.metadata.get(EXTRA_METADATA_KEY)


def coerce_extra_metadata(
    viewer: 'ViewerModel', layer: 'Layer'
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


def is_metadata_equal_to_original(layer: Optional['Layer']) -> bool:
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
    return layer.name == extras.original.name
