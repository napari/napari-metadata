from enum import Enum, auto
from typing import Optional

import pint
from pint.registry import ApplicationRegistry

from napari_metadata._model import get_pint_ureg


class TimeUnits(Enum):
    """Supported units for a temporal axis."""

    FEMTOSECOND = auto()
    PICOSECOND = auto()
    NANOSECOND = auto()
    MICROSECOND = auto()
    MILLISECOND = auto()
    SECOND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()
    YEAR = auto()
    DECADE = auto()
    CENTURY = auto()
    MILLENNIUM = auto()

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_name(cls, name: str) -> Optional['TimeUnits']:
        for m in cls:
            if str(m) == name:
                return m
        return None

    @classmethod
    def names(cls) -> list[str]:
        return [str(m) for m in cls]

    @classmethod
    def enums(cls) -> list['TimeUnits']:
        return list(cls)

    @classmethod
    def pint_units(cls) -> list[pint.Unit]:
        unit_registry: ApplicationRegistry = get_pint_ureg()
        units: list[pint.Unit] = []
        for name in cls.names():
            if name == 'none':
                units.append(unit_registry.Unit(''))
            else:
                units.append(unit_registry.Unit(name))
        return units

    @classmethod
    def contains(cls, name: str) -> bool:
        return name in cls.names()

    @classmethod
    def default_unit(cls) -> str:
        return 'second'
