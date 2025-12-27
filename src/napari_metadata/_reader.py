"""Defines napari reader contributions that handle extra metadata.

The code in this module is vendored from v0.5.2 of napari-ome-zarr.
Modifications are indicated inline with the `MOD:` prefix.
The license for the original code from napari-ome-zarr is below.

----------------------------

Copyright (c) 2021, OME Team
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of napari-ome-zarr nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import contextlib
import logging
import warnings
from collections.abc import Iterator
from copy import deepcopy
from typing import Any, Optional

import numpy as np
from ome_zarr.io import parse_url
from ome_zarr.reader import Label, Node, Reader
from ome_zarr.types import LayerData, PathLike, ReaderFunction
from vispy.color import Colormap

from ._model import (
    EXTRA_METADATA_KEY,
    Axis,
    ExtraMetadata,
    OriginalMetadata,
    SpaceAxis,
    TimeAxis,
)
from ._space_units import SpaceUnits
from ._time_units import TimeUnits

# MOD: change the name of the reader for this module.
LOGGER = logging.getLogger('napari_metadata._reader')

# NB: color for labels, colormap for images
# MOD: remove name from these, since it's a bit special.
METADATA_KEYS = (
    'name',
    'visible',
    'contrast_limits',
    'colormap',
    'color',
    'metadata',
)


def napari_get_reader(path: PathLike) -> Optional[ReaderFunction]:
    """Returns a reader for supported paths that include IDR ID.
    - URL of the form: https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.1/ID.zarr/
    The reader can be then be called using the path to read the file.

    >>> reader = napari_get_reader(path)
    >>> layer_list = reader(path)

    """
    if isinstance(path, list):
        if len(path) > 1:
            warnings.warn(
                'more than one path is not currently supported', stacklevel=2
            )
        path = path[0]
    zarr = parse_url(path)
    if zarr:
        reader = Reader(zarr)
        return transform(reader())
    # Ignoring this path
    return None


def transform_properties(
    props: Optional[dict[str, dict]] = None,
) -> Optional[dict[str, list]]:
    """
    Transform properties
    Transform a dict of {label_id : {key: value, key2: value2}}
    with a key for every LABEL
    into a dict of a key for every VALUE, with a list of values for each
    .. code::
        {
            "index": [1381342, 1381343...]
            "omero:roiId": [1381342, 1381343...],
            "omero:shapeId": [1682567, 1682567...]
        }
    """
    if props is None:
        return None

    properties: dict[str, list] = {}

    # First, create lists for all existing keys...
    for _, props_dict in props.items():
        for key in props_dict:
            properties[key] = []

    keys = list(properties.keys())

    properties['index'] = []
    for label_id, props_dict in props.items():
        properties['index'].append(label_id)
        # ...in case some objects don't have all the keys
        for key in keys:
            properties[key].append(props_dict.get(key, None))
    return properties


def transform_scale(
    node_metadata: dict, metadata: dict, channel_axis: Optional[int]
) -> None:
    """
    e.g. transformation is {"scale": [0.2, 0.06, 0.06]}
    Get a list of these for each level in data. Just use first?
    """
    if 'coordinateTransformations' in node_metadata:
        level_0_transforms = node_metadata['coordinateTransformations'][0]
        for transf in level_0_transforms:
            if 'scale' in transf:
                scale = transf['scale']
                if channel_axis is not None:
                    scale.pop(channel_axis)
                metadata['scale'] = tuple(scale)
            if 'translation' in transf:
                translate = transf['translation']
                if channel_axis is not None:
                    translate.pop(channel_axis)
                metadata['translate'] = tuple(translate)


def transform(nodes: Iterator[Node]) -> Optional[ReaderFunction]:
    def f(*args: Any, **kwargs: Any) -> list[LayerData]:
        results: list[LayerData] = []

        for node in nodes:
            data: list[Any] = node.data
            metadata: dict[str, Any] = {}
            if data is None or len(data) < 1:
                LOGGER.debug('skipping non-data %s', node)
            else:
                LOGGER.debug('transforming %s', node)
                LOGGER.debug('node.metadata: %s', node.metadata)

                layer_type: str = 'image'
                channel_axis = None
                try:
                    ch_types = [axis['type'] for axis in node.metadata['axes']]
                    if 'channel' in ch_types:
                        channel_axis = ch_types.index('channel')
                except Exception:
                    LOGGER.error('Error reading axes: Please update ome-zarr')
                    raise

                transform_scale(node.metadata, metadata, channel_axis)

                # MOD: squeeze a single level image.
                if isinstance(data, list) and len(data) == 1:
                    data = data[0]

                # MOD: ensure that name is a list to handle single channel.
                if (
                    (name := node.metadata.get('name'))
                    and channel_axis is None
                    and isinstance(name, str)
                ):
                    node.metadata['name'] = [name]

                if node.load(Label):
                    layer_type = 'labels'
                    for x in METADATA_KEYS:
                        if x in node.metadata:
                            metadata[x] = node.metadata[x]
                    if channel_axis is not None:
                        data = [
                            np.squeeze(level, axis=channel_axis)
                            for level in node.data
                        ]

                    # MOD: napari images don't support properties.
                    properties = transform_properties(
                        node.metadata.get('properties')
                    )
                    if properties is not None:
                        metadata['properties'] = properties

                else:
                    # Handle the removal of vispy requirement from ome-zarr-py
                    cms = node.metadata.get('colormap', [])
                    for idx, cm in enumerate(cms):
                        if not isinstance(cm, Colormap):
                            cms[idx] = Colormap(cm)

                    if channel_axis is not None:
                        # multi-channel; Copy known metadata values
                        metadata['channel_axis'] = channel_axis
                        for x in METADATA_KEYS:
                            if x in node.metadata:
                                metadata[x] = node.metadata[x]
                    else:
                        # single channel image, so metadata just needs
                        # single items (not lists)
                        for x in METADATA_KEYS:
                            if x in node.metadata:
                                with contextlib.suppress(Exception):
                                    metadata[x] = node.metadata[x][0]

                # MOD: this plugin provides somewhere to put the axes
                # and some extra metadata. We create an instance of extra
                # metadata per channel.
                axes = get_axes(node.metadata)
                if channel_axis is None:
                    if 'metadata' not in metadata:
                        metadata['metadata'] = {}
                    name = metadata.get('name')
                    metadata['metadata'][EXTRA_METADATA_KEY] = make_extras(
                        metadata=metadata,
                        axes=axes,
                        name=name,
                    )
                else:
                    n_channels = (
                        data[0] if isinstance(data, list) else data
                    ).shape[channel_axis]
                    meta = metadata.get('metadata', {})
                    if not isinstance(meta, list):
                        metadata['metadata'] = [deepcopy(meta)] * n_channels
                    name = metadata.get('name')
                    if not isinstance(name, list):
                        name = [name] * n_channels
                    for n, m in zip(name, metadata['metadata'], strict=False):
                        m[EXTRA_METADATA_KEY] = make_extras(
                            metadata=metadata,
                            axes=axes,
                            name=n,
                        )

                rv: LayerData = (data, metadata, layer_type)
                LOGGER.debug('Transformed: %s', rv)
                results.append(rv)

        return results

    return f


def make_extras(
    *, metadata: dict, axes: list[Axis], name: Optional[str]
) -> ExtraMetadata:
    scale = tuple(metadata['scale']) if 'scale' in metadata else None
    translate = (
        tuple(metadata['translate']) if 'translate' in metadata else None
    )
    original_meta = OriginalMetadata(
        axes=deepcopy(axes),
        name=name,
        scale=scale,
        translate=translate,
    )
    return ExtraMetadata(
        axes=deepcopy(axes),
        original=original_meta,
    )


def get_axes(metadata: dict) -> list[Axis]:
    axes = []
    for a in metadata['axes']:
        if axis := get_axis(a):
            axes.append(axis)
    space_axes = tuple(axis for axis in axes if isinstance(axis, SpaceAxis))
    space_units = {axis.get_unit_name() for axis in space_axes}
    if len(space_units) > 1:
        warnings.warn(
            f'Found mixed spatial units: {space_units}. '
            'Using none for all instead.',
            UserWarning,
            stacklevel=2,
        )
        for axis in space_axes:
            axis.unit = SpaceUnits.NONE
    return axes


def get_axis(axis: dict) -> Optional[Axis]:
    name = axis['name']
    unit = axis.get('unit', 'none')
    axis_type = axis.get('type')
    if axis_type == 'time':
        return TimeAxis(name=name, unit=TimeUnits.from_name(unit))
    elif axis_type != 'channel':
        return SpaceAxis(name=name, unit=SpaceUnits.from_name(unit))
    return None
