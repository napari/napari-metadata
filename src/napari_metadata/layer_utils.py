"""Helpers for reading and writing napari layer metadata.

Only non-trivial helpers live here — functions that do validation,
clamping, or handle sequence/array polymorphism.  Trivial property
access (``layer.axis_labels``, ``layer.scale``, etc.) should be done
directly at call sites.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from napari.layers import Layer


def set_axes_scales(
    layer: Layer,
    axes_scales: tuple[float, ...],
) -> None:
    """Set axis scales on *layer* with clamping and type validation.

    Non-positive values are clamped to ``0.001``.  Non-numeric values
    cause the call to be silently ignored.
    """
    for scale in axes_scales:
        if not isinstance(scale, int | float):
            return

    clamped = tuple(max(s, 0.001) for s in axes_scales)
    layer.scale = np.array(clamped)


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


def get_layer_source_path(layer: Layer) -> str:
    """Get the source path of the layer if available."""
    if layer.source.path is None:
        return ''
    return layer.source.path
