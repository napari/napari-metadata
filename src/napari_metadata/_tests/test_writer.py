from collections.abc import Sequence
from typing import Optional

import numpy as np
import pytest
from napari.layers import Image
from npe2.types import ArrayLike
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader

from .._model import (
    EXTRA_METADATA_KEY,
    ExtraMetadata,
    SpaceAxis,
    SpaceUnits,
    TimeAxis,
    TimeUnits,
)
from .._writer import write_image


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def path(tmp_path) -> str:
    return str(tmp_path / 'test.zarr')


def read_ome_zarr(path: str) -> tuple[Sequence[ArrayLike], dict]:
    reader = Reader(parse_url(path))
    nodes = list(reader())
    node = nodes[0]
    data = list(node.data)
    metadata = node.metadata
    return data, metadata


def ome_axis_names(ome_metadata: dict) -> tuple[str, ...]:
    return tuple(a['name'] for a in ome_metadata['axes'])


def ome_axis_types(ome_metadata: dict) -> tuple[Optional[str], ...]:
    return tuple(a.get('type') for a in ome_metadata['axes'])


def ome_axis_units(ome_metadata: dict) -> tuple[Optional[str], ...]:
    return tuple(a.get('unit') for a in ome_metadata['axes'])


def ome_transforms(ome_metadata: dict) -> tuple[float, ...]:
    return ome_metadata['coordinateTransformations'][0]


def test_write_2d_image_without_extras(rng, path):
    image = Image(rng.random((5, 6)))
    data, metadata, _ = image.as_layer_data_tuple()

    paths_written = write_image(path, data, metadata)

    assert len(paths_written) == 1
    assert paths_written[0] == path

    read_data, read_metadata = read_ome_zarr(path)

    assert len(read_data) == 1
    np.testing.assert_array_equal(read_data[0], data)

    # The default/magic name that napari gives the layer is not
    # in our control and we always write it.
    assert read_metadata['name'] == 'Image'

    assert ome_axis_names(read_metadata) == ('0', '1')
    assert ome_axis_types(read_metadata) == ('space', 'space')
    assert ome_axis_units(read_metadata) == (None, None)

    transforms = read_metadata['coordinateTransformations'][0]
    assert len(transforms) == 2
    assert tuple(transforms[0]['scale']) == (1, 1)
    assert tuple(transforms[1]['translation']) == (0, 0)


def test_write_2d_image_with_extras(rng, path):
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

    read_data, read_metadata = read_ome_zarr(path)

    assert len(read_data) == 1
    np.testing.assert_array_equal(read_data[0], data)

    assert read_metadata['name'] == 'kermit'

    assert ome_axis_names(read_metadata) == ('y', 'x')
    assert ome_axis_types(read_metadata) == ('space', 'space')
    assert ome_axis_units(read_metadata) == ('millimeter', 'millimeter')

    transforms = read_metadata['coordinateTransformations']
    assert len(transforms) == 1
    assert len(transforms[0]) == 2
    assert tuple(transforms[0][0]['scale']) == (2, 3)
    assert tuple(transforms[0][1]['translation']) == (-1, 1)


def test_write_multiscale_2d_image_with_extras(rng, path):
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

    read_data, read_metadata = read_ome_zarr(path)

    assert len(read_data) == len(data) == 2
    np.testing.assert_array_equal(read_data[0], data[0])
    np.testing.assert_array_equal(read_data[1], data[1])

    assert read_metadata['name'] == 'momo'

    assert ome_axis_names(read_metadata) == ('y', 'x')
    assert ome_axis_types(read_metadata) == ('space', 'space')
    assert ome_axis_units(read_metadata) == ('millimeter', 'millimeter')

    transforms = read_metadata['coordinateTransformations']
    assert len(transforms) == 2

    transforms_hi_res = transforms[0]
    assert len(transforms_hi_res) == 2
    assert tuple(transforms_hi_res[0]['scale']) == (2, 3)
    assert tuple(transforms_hi_res[1]['translation']) == (-1, 1)

    transforms_lo_res = transforms[1]
    assert len(transforms_lo_res) == 2
    assert tuple(transforms_lo_res[0]['scale']) == (4, 6)
    assert tuple(transforms_lo_res[1]['translation']) == (-1, 1)


def test_write_3d_image_with_extras(rng, path):
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

    read_data, read_metadata = read_ome_zarr(path)

    assert len(read_data) == 1
    np.testing.assert_array_equal(read_data[0], data)

    assert read_metadata['name'] == 'sandy'

    assert ome_axis_names(read_metadata) == ('t', 'y', 'x')
    assert ome_axis_types(read_metadata) == ('time', 'space', 'space')
    assert ome_axis_units(read_metadata) == (
        'second',
        'millimeter',
        'millimeter',
    )

    transforms = read_metadata['coordinateTransformations']
    assert len(transforms) == 1
    assert len(transforms[0]) == 2
    assert tuple(transforms[0][0]['scale']) == (1, 3, 4)
    assert tuple(transforms[0][1]['translation']) == (9000, -1, 1)
