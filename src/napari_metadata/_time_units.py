from enum import Enum, auto
from typing import Optional


class TimeUnits(Enum):
    """Supported units for a temporal axis."""

    NONE = auto()
    NANOSECOND = auto()
    MICROSECOND = auto()
    MILLISECOND = auto()
    SECOND = auto()

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
