from enum import Enum, auto
from typing import Optional

from napari_metadata._space_units import SpaceUnits
from napari_metadata._time_units import TimeUnits

PossibleUnitEnum = type[SpaceUnits] | type[TimeUnits]


class AxisType(Enum):
    """Supported axis types."""

    SPACE = auto()
    TIME = auto()
    STRING = auto()

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_name(cls, name: str) -> Optional['AxisType']:
        for m in cls:
            if str(m) == name:
                return m
        return None

    @classmethod
    def names(cls) -> list[str]:
        return [str(m) for m in cls]

    @classmethod
    def enums(cls) -> list['AxisType']:
        return list(cls)

    def unit_enum(self) -> PossibleUnitEnum | None:
        unit_maps: dict[AxisType, PossibleUnitEnum | None] = {
            AxisType.SPACE: SpaceUnits,
            AxisType.TIME: TimeUnits,
            AxisType.STRING: None,
        }
        return unit_maps[self]
