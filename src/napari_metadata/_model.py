from collections.abc import Callable, Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, cast

import numpy as np
import pint
from pint.registry import ApplicationRegistry

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


def resolve_layer(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> 'Layer | None':
    """Helper to resolve which layer to use: explicit layer or active layer."""
    if layer is not None:
        return layer
    return viewer.layers.selection.active


def get_layers_list(viewer: 'ViewerModel') -> list['Layer']:
    """Get a list of all layers in the viewer."""
    layer_name_list: list[Layer] = list(viewer.layers)
    return layer_name_list


def get_axes_labels(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[str, ...]:
    """Get axis labels from the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    return resolved_layer.axis_labels if resolved_layer is not None else ()


def set_axes_labels(
    viewer: 'ViewerModel',
    axes_labels: tuple[str, ...],
    layer: 'Layer | None' = None,
) -> None:
    """Set axis labels on the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    if resolved_layer is not None:
        resolved_layer.axis_labels = axes_labels


APPLICATION_REGISTRY: ApplicationRegistry = pint.get_application_registry()


def get_pint_ureg() -> pint.registry.ApplicationRegistry:
    return APPLICATION_REGISTRY


def get_axes_units(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[pint.Unit | None, ...]:
    """Get axis units from the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    return resolved_layer.units if resolved_layer is not None else ()


def set_axes_units(
    viewer: 'ViewerModel',
    axes_units: tuple[str, ...],
    layer: 'Layer | None' = None,
) -> None:
    """Set axis units on the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    if resolved_layer is not None:
        resolved_layer.units = axes_units


def get_axes_scales(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[float, ...]:
    """Get axis scales from the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    return (
        cast(tuple[float, ...], resolved_layer.scale)
        if resolved_layer is not None
        else ()
    )


def set_axes_scales(
    viewer: 'ViewerModel',
    axes_scales: tuple[float, ...],
    layer: 'Layer | None' = None,
) -> None:
    """Set axis scales on the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    if resolved_layer is None:
        return

    for scale in axes_scales:
        if not isinstance(scale, float):
            return
        if scale <= 0:
            scale = 0.001

    resolved_layer.scale = np.array(axes_scales)


def get_axes_translations(
    viewer: 'ViewerModel', layer: 'Layer | None' = None
) -> tuple[float, ...]:
    """Get axis translations from the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    return (
        cast(tuple[float, ...], resolved_layer.translate)
        if resolved_layer is not None
        else ()
    )


def set_axes_translations(
    viewer: 'ViewerModel',
    axes_translations: tuple[float, ...],
    layer: 'Layer | None' = None,
) -> None:
    """Set axis translations on the specified layer or active layer."""
    resolved_layer = resolve_layer(viewer, layer)
    if resolved_layer is not None:
        resolved_layer.translate = axes_translations


def get_layer_data_shape(layer: 'Layer | None') -> tuple[int, ...]:
    """Get the shape of the layer's data."""
    if layer is None:
        return ()

    if hasattr(layer.data, 'shape'):
        return layer.data.shape
    if isinstance(layer.data, Sequence):
        return (len(layer.data),)
    return ()


def get_layer_data_dtype(layer: 'Layer | None') -> str:
    """Get the dtype of the layer's data as a string."""
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
    """Get the source path of the layer if available."""
    if layer is None or layer.source.path is None:
        return ''
    return layer.source.path


def get_layer_dimensions(layer: 'Layer | None') -> int:
    """Get the number of dimensions in the layer."""
    return layer.ndim if layer is not None else 0


def connect_callback_to_layer_selection_events(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    """Connect a callback to layer selection change events."""
    viewer.layers.selection.events.active.connect(cb_function)


def disconnect_callback_to_layer_selection_events(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    """Disconnect a callback from layer selection change events."""
    with suppress(TypeError, ValueError):
        viewer.layers.selection.events.active.disconnect(cb_function)


def connect_callback_to_list_events(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    """Connect a callback to layer list change events (inserted, removed, changed)."""
    viewer.layers.events.inserted.connect(cb_function)
    viewer.layers.events.removed.connect(cb_function)
    viewer.layers.events.changed.connect(cb_function)


def disconnect_callback_to_list_events(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    with suppress(TypeError, ValueError):
        viewer.layers.events.inserted.disconnect(cb_function)
    with suppress(TypeError, ValueError):
        viewer.layers.events.removed.disconnect(cb_function)
    with suppress(TypeError, ValueError):
        viewer.layers.events.changed.disconnect(cb_function)


def connect_callback_to_layer_selection_changed(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    """Connect a callback to layer name change Aevent."""
    viewer.layers.selection.events.active.connect(cb_function)


def disconnect_callback_to_layer_selection_changed(
    viewer: 'ViewerModel', cb_function: Callable
) -> None:
    """Disconnect a callback from layer name change event."""
    with suppress(TypeError, ValueError):
        viewer.layers.selection.events.active.disconnect(cb_function)


def connect_callback_to_layer_name_changed(
    viewer: 'ViewerModel', cb_function: Callable, layer: 'Layer | None' = None
) -> None:
    """Connect a callback function to the specified layer or the current layer name event"""
    resolved_layer = resolve_layer(viewer, layer)
    if resolved_layer is None:
        return
    resolved_layer.events.name.connect(cb_function)


def disconnect_callback_to_layer_name_changed(
    viewer: 'ViewerModel', cb_function: Callable, layer: 'Layer | None'
) -> None:
    """Disconnect a callback function from the specified layer name event"""
    if layer is None:
        return
    with suppress(TypeError, ValueError):
        layer.events.name.disconnect(cb_function)
