from enum import Enum, auto
from typing import List, Optional


class SpaceUnits(Enum):
    """Supported units for a spatial axis."""

    NONE = auto()
    PIXEL = auto()
    FEMTOMETER = auto()
    PICOMETER = auto()
    NANOMETER = auto()
    MICROMETER = auto()
    MILLIMETER = auto()
    CENTIMETER = auto()
    METER = auto()

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_name(cls, name: str) -> Optional["SpaceUnits"]:
        for m in cls:
            if str(m) == name:
                return m
        return None

    @classmethod
    def names(cls) -> List[str]:
        return [str(m) for m in cls]
    
    @classmethod
    def contains(cls, name: str) -> bool:
        return name in cls.names()
