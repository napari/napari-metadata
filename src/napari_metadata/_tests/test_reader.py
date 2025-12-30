import numpy as np
import pytest
from napari.layers import Image
from npe2.types import LayerData

from .._model import (
    EXTRA_METADATA_KEY,
    ChannelAxis,
    ExtraMetadata,
    SpaceAxis,
    SpaceUnits,
    TimeAxis,
    TimeUnits,
)
from .._reader import napari_get_reader
from .._writer import write_image


def read_ome_zarr(path: str) -> list[LayerData]:
    """Gets the napari reader and uses it to read the file at path.

    Returns
    -------
    LayerData tuple. List of layer tuples with the form:
        [(data, metadata, layer_type)] where data is np.array or dask.array,
        metadata is dict, and layer_type is str.
        See https://napari.org/stable/plugins/guides.html#the-layerdata-tuple
        for full documentation.
    """
    reader = napari_get_reader(path)
    return reader(path)


def test_read_2d_image_without_extras(rng, path):
    image = Image(rng.random((5, 6)))
    data, metadata, _ = image.as_layer_data_tuple()
    paths_written = write_image(path, data, metadata)
    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_layers = read_ome_zarr(path)

    assert len(read_layers) == 1
    read_data, _, _ = read_layers[0]
    np.testing.assert_array_equal(read_data, data)


def test_read_2d_image_with_extras(rng, path):
    image = Image(
        rng.random((5, 6)),
        name='kermit',
        scale=(2, 3),
        translate=(-1, 1),
    )
    data, metadata, _ = image.as_layer_data_tuple()
    extras = ExtraMetadata(
        axes=[
            SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
            SpaceAxis(name='x', unit=SpaceUnits.MILLIMETER),
        ],
    )
    metadata['metadata'][EXTRA_METADATA_KEY] = extras
    paths_written = write_image(path, data, metadata)
    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_layers = read_ome_zarr(path)

    assert len(read_layers) == 1
    read_data, read_metadata, _ = read_layers[0]
    np.testing.assert_array_equal(read_data, data)

    assert read_metadata['name'] == 'kermit'
    assert read_metadata['scale'] == (2, 3)
    assert read_metadata['translate'] == (-1, 1)

    read_extras: ExtraMetadata = read_metadata['metadata'][EXTRA_METADATA_KEY]
    assert len(read_extras.axes) == 2
    assert read_extras.axes[0] == extras.axes[0]
    assert read_extras.axes[1] == extras.axes[1]


def test_read_multiscale_2d_image_with_extras(rng, path):
    image = Image(
        [rng.random((10, 12)), rng.random((5, 6))],
        name='momo',
        scale=(2, 3),
        translate=(-1, 1),
    )
    data, metadata, _ = image.as_layer_data_tuple()
    extras = ExtraMetadata(
        axes=[
            SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
            SpaceAxis(name='x', unit=SpaceUnits.MILLIMETER),
        ],
    )
    metadata['metadata'][EXTRA_METADATA_KEY] = extras
    paths_written = write_image(path, data, metadata)
    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_layers = read_ome_zarr(path)

    assert len(read_layers) == 1
    read_data, read_metadata, _ = read_layers[0]
    assert len(read_data) == 2
    np.testing.assert_array_equal(read_data[0], data[0])
    np.testing.assert_array_equal(read_data[1], data[1])

    assert read_metadata['name'] == 'momo'
    assert read_metadata['scale'] == (2, 3)
    assert read_metadata['translate'] == (-1, 1)

    read_extras: ExtraMetadata = read_metadata['metadata'][EXTRA_METADATA_KEY]
    assert len(read_extras.axes) == 2
    assert read_extras.axes[0] == extras.axes[0]
    assert read_extras.axes[1] == extras.axes[1]


def test_read_3d_image_with_extras(rng, path):
    image = Image(
        rng.random((5, 6, 7)),
        name='sandy',
        scale=(1, 3, 4),
        translate=(9000, -1, 1),
    )
    data, metadata, _ = image.as_layer_data_tuple()
    extras = ExtraMetadata(
        axes=[
            TimeAxis(name='t', unit=TimeUnits.SECOND),
            SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
            SpaceAxis(name='x', unit=SpaceUnits.MILLIMETER),
        ],
    )
    metadata['metadata'][EXTRA_METADATA_KEY] = extras
    paths_written = write_image(path, data, metadata)
    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_layers = read_ome_zarr(path)

    assert len(read_layers) == 1
    read_data, read_metadata, _ = read_layers[0]
    np.testing.assert_array_equal(read_data, data)

    assert read_metadata['name'] == 'sandy'
    assert read_metadata['scale'] == (1, 3, 4)
    assert read_metadata['translate'] == (9000, -1, 1)

    read_extras: ExtraMetadata = read_metadata['metadata'][EXTRA_METADATA_KEY]
    assert len(read_extras.axes) == 3
    assert read_extras.axes[0] == extras.axes[0]
    assert read_extras.axes[1] == extras.axes[1]
    assert read_extras.axes[2] == extras.axes[2]


def test_read_2d_image_with_mixed_space_units(rng, path):
    image = Image(np.zeros((5, 6)))
    data, metadata, _ = image.as_layer_data_tuple()
    extras = ExtraMetadata(
        axes=[
            SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
            SpaceAxis(name='x', unit=SpaceUnits.METER),
        ],
    )
    metadata['metadata'][EXTRA_METADATA_KEY] = extras
    write_image(path, data, metadata)

    with pytest.warns(UserWarning):
        read_layers = read_ome_zarr(path)
    _, read_metadata, _ = read_layers[0]

    read_extras: ExtraMetadata = read_metadata['metadata'][EXTRA_METADATA_KEY]
    assert read_extras.axes[0] == SpaceAxis(name='y', unit=SpaceUnits.NONE)
    assert read_extras.axes[1] == SpaceAxis(name='x', unit=SpaceUnits.NONE)


def test_read_multichannel_2d_image_with_extras(rng, path):
    image = Image(
        rng.random((2, 6, 7)),
        name='whisper',
        scale=(1, 3, 4),
        translate=(0, -1, 1),
    )
    data, metadata, _ = image.as_layer_data_tuple()
    extras = ExtraMetadata(
        axes=[
            ChannelAxis(name='c'),
            SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
            SpaceAxis(name='x', unit=SpaceUnits.MILLIMETER),
        ],
    )
    metadata['metadata'][EXTRA_METADATA_KEY] = extras
    paths_written = write_image(path, data, metadata)
    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_layers = read_ome_zarr(path)

    assert len(read_layers) == 1
    read_data, read_metadata, _ = read_layers[0]
    np.testing.assert_array_equal(read_data, data)

    assert read_metadata['name'] == 'whisper'
    assert read_metadata['scale'] == (3, 4)
    assert read_metadata['translate'] == (-1, 1)
    assert read_metadata['channel_axis'] == 0

    # One metadata dict for each output layer.
    assert len(read_metadata['metadata']) == 2
    # Check details of the first one.
    read_extras = read_metadata['metadata'][0][EXTRA_METADATA_KEY]
    assert len(read_extras.axes) == 2
    assert read_extras.axes[0] == extras.axes[1]
    assert read_extras.axes[1] == extras.axes[2]
    # Check the other is the same.
    assert read_extras == read_metadata['metadata'][1][EXTRA_METADATA_KEY]
