from collections.abc import Sequence
from typing import (
    TYPE_CHECKING,
    Tuple,
    cast,
)

import numpy as np
import pint

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


def get_axes_labels(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> Tuple[str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.axis_labels


def set_active_layer_axes_labels(
    viewer: 'ViewerModel', axes_labels: Tuple[str, ...]
):
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    layer.axis_labels = axes_labels


def get_pint_ureg(viewer: 'ViewerModel') -> pint.UnitRegistry | None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return None
    layer_units = layer.units
    for unit in layer_units:
        if isinstance(unit, str):
            continue
        else:
            unit_reg = unit._REGISTRY
            return unit_reg


def get_axes_units(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> Tuple[pint.Unit | str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.units


def set_active_layer_axes_units(
    viewer: 'ViewerModel', axes_units: Tuple[str, ...]
) -> None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    layer.units = axes_units


def get_axes_scales(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> Tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(Tuple[float, ...], active_layer.scale)


def set_active_layer_axes_scales(
    viewer: 'ViewerModel', axes_scales: Tuple[float, ...]
) -> None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    for scale in axes_scales:
        if not isinstance(scale, float):
            return
        if scale <= 0:
            scale = 0.001
    layer.scale = np.array(axes_scales)


def get_axes_translations(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> Tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(Tuple[float, ...], active_layer.translate)


def set_active_layer_axes_translations(
    viewer: 'ViewerModel', axes_translations: Tuple[float, ...]
) -> None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    layer.translate = axes_translations


def get_layer_data_shape(layer: 'Layer | None') -> Tuple[int, ...]:
    if layer is None:
        return ()
    layer_data = layer.data
    if hasattr(layer_data, 'shape'):
        return layer_data.shape
    if isinstance(layer_data, Sequence):
        return (len(layer_data),)
    return ()


def get_layer_data_dtype(layer: 'Layer | None') -> str:
    if layer is None:
        return ''
    layer_data = layer.data
    if hasattr(layer_data, 'dtype'):
        return str(layer_data.dtype)
    if (
        isinstance(layer_data, Sequence)
        and len(layer_data) > 0
        and hasattr(layer_data[0], 'dtype')
    ):
        return str(layer_data[0].dtype)
    return 'Unknown'


def get_layer_source_path(layer: 'Layer | None') -> str:
    if layer is None:
        return ''
    if layer.source.path is None:
        return ''
    return layer.source.path


def get_layer_dimensions(layer: 'Layer | None') -> int:
    if layer is None:
        return 0
    return layer.ndim


def get_active_layer(viewer: 'ViewerModel') -> 'Layer | None':
    return viewer.layers.selection.active
