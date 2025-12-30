from enum import Enum, auto
from typing import Optional


class TimeUnits(Enum):
    """Supported units for a temporal axis."""

    NONE = auto()
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
    def contains(cls, name: str) -> bool:
        return name in cls.names()