"""Helpers for reading and writing napari layer metadata.

Only non-trivial helpers live here — functions that handle
sequence/array polymorphism.  Trivial property access
(``layer.axis_labels``, ``layer.scale``, etc.) should be done
directly at call sites.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from napari.layers import Layer


def get_layer_data_shape(layer: Layer) -> tuple[int, ...]:
    """Get the shape of the layer's data."""
    if hasattr(layer.data, 'shape'):
        return layer.data.shape
    if isinstance(layer.data, Sequence):
        return (len(layer.data),)
    return ()


def get_layer_data_dtype(layer: Layer) -> str:
    """Get the dtype of the layer's data as a string."""
    layer_data = layer.data
    if hasattr(layer_data, 'dtype'):
        return layer_data.dtype.name
    if (
        isinstance(layer_data, Sequence)
        and len(layer_data) > 0
        and hasattr(layer_data[0], 'dtype')
    ):
        return layer_data[0].dtype.name
    return 'Unknown'
