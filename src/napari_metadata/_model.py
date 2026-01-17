from collections.abc import Sequence
from typing import TYPE_CHECKING, cast
from collections.abc import Callable
from contextlib import suppress

import numpy as np
import pint

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


def get_axes_labels(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.axis_labels


def set_active_layer_axes_labels(
    viewer: 'ViewerModel', axes_labels: tuple[str, ...]
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
) -> tuple[pint.Unit | str, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return active_layer.units


def set_active_layer_axes_units(
    viewer: 'ViewerModel', axes_units: tuple[str, ...]
) -> None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    layer.units = axes_units


def get_axes_scales(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(tuple[float, ...], active_layer.scale)


def set_active_layer_axes_scales(
    viewer: 'ViewerModel', axes_scales: tuple[float, ...]
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
) -> tuple[float, ...]:
    active_layer = None
    if layer is None:
        active_layer = get_active_layer(viewer)
        if active_layer is None:
            return ()
    else:
        active_layer = layer
    return cast(tuple[float, ...], active_layer.translate)


def set_active_layer_axes_translations(
    viewer: 'ViewerModel', axes_translations: tuple[float, ...]
) -> None:
    layer: Layer | None = get_active_layer(viewer)
    if layer is None:
        return
    layer.translate = axes_translations


def get_layer_data_shape(layer: 'Layer | None') -> tuple[int, ...]:
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


def get_layers_list(viewer: 'ViewerModel') -> list['Layer']:
    layer_name_list: list[Layer] = list(viewer.layers)
    return layer_name_list


def connect_callback_to_layer_selection_events(
    viewer: 'ViewerModel', cb_function: Callable
):
    viewer.layers.selection.events.active.connect(cb_function)


def disconnect_callback_to_layer_selection_events(
    viewer: 'ViewerModel', cb_function: Callable
):
    with suppress(TypeError, ValueError):
        viewer.layers.selection.events.active.disconnect(cb_function)


def connect_callback_to_list_events(
    viewer: 'ViewerModel', cb_function: Callable
):
    viewer.layers.events.inserted.connect(cb_function)
    viewer.layers.events.removed.connect(cb_function)
    viewer.layers.events.changed.connect(cb_function)


def disconnect_callback_to_list_events(
    viewer: 'ViewerModel', cb_function: Callable
):
    with suppress(TypeError, ValueError):
        viewer.layers.events.inserted.disconnect(cb_function)
    with suppress(TypeError, ValueError):
        viewer.layers.events.removed.connect(cb_function)
    with suppress(TypeError, ValueError):
        viewer.layers.events.changed.connect(cb_function)
