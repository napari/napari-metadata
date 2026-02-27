"""Axis classification and curated unit configuration for napari-metadata.

``AxisType`` is an ``Enum`` whose members classify axes as SPACE, TIME, or
STRING.  SPACE and TIME members carry a ``_UnitConfig`` dataclass as their
``.value``, encoding the exact set of units shown in the UI and a sensible
default.  STRING axes take arbitrary pint-parseable text; their ``.value``
is ``None``.

The ``_UnitConfig`` dataclass also provides ``pint_units()``, so callers that
need ``pint.Unit`` objects can get them without importing pint at the top of
their own module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from typing_extensions import Self

import pint


@dataclass(frozen=True)
class _UnitConfig:
    """Curated unit list and sensible default for one axis category.

    ``units`` is the ordered sequence shown in the UI dropdown.
    ``default`` is the fallback when no unit has been set yet.
    Both carry pint-registered names so ``pint_units()`` always succeeds.
    """

    units: tuple[str, ...]
    default: str

    def pint_units(self) -> list[pint.Unit]:
        """Return a ``pint.Unit`` for every configured unit string."""
        ureg = pint.get_application_registry()
        return [ureg.Unit(u) for u in self.units]


class AxisUnitEnum(Enum):
    """Classifies an axis as spatial, temporal, or free-form string.

    SPACE and TIME carry a ``_UnitConfig`` as ``.value``; access the curated
    unit list with ``axis_type.value.units``, the default with
    ``axis_type.value.default``, and pint objects with
    ``axis_type.value.pint_units()``.

    STRING axes accept arbitrary text; ``axis_type.value`` is ``None``.
    """

    SPACE = _UnitConfig(
        units=(
            'pixel', 'femtometer', 'picometer', 'nanometer',
            'micrometer', 'millimeter', 'centimeter', 'meter',
        ),
        default='pixel',
    )
    TIME = _UnitConfig(
        units=(
            'femtosecond', 'picosecond', 'nanosecond', 'microsecond',
            'millisecond', 'second', 'minute', 'hour',
            'day', 'year', 'decade', 'century', 'millennium',
        ),
        default='second',
    )
    STRING = None

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_name(cls, name: str) -> Optional[Self]:
        """Return the member whose ``str()`` matches *name*, or ``None``."""
        for m in cls:
            if str(m) == name:
                return m
        return None

    @classmethod
    def names(cls) -> list[str]:
        """Return lower-case string names of all members."""
        return [str(m) for m in cls]
