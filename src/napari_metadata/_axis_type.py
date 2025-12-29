from enum import Enum, auto
from typing import Optional


class AxisType(Enum):
    """Supported axis types."""

    SPACE = auto()
    TIME = auto()
    CHANNEL = auto()

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
