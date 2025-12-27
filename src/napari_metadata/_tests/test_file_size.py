import numpy as np
import pytest
from napari.layers import Image

from napari_metadata._file_size import (
    directory_size,
    generate_display_size,
    generate_text_for_size,
)
from napari_metadata._model import (
    EXTRA_METADATA_KEY,
    ExtraMetadata,
    SpaceAxis,
    SpaceUnits,
)
from napari_metadata._reader import napari_get_reader
from napari_metadata._writer import write_image


@pytest.fixture
def local_zarr_path(path):
    image = Image(
        np.zeros((5, 6)),
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
    return paths_written[0]


def test_local_file_new(local_zarr_path):
    reader = napari_get_reader(local_zarr_path)
    layerdata_tuples = reader(
        local_zarr_path
    )  # [(data, metadata, layer_type)]
    data, metadata, layer_type = layerdata_tuples[0]

    layer = Image(data, metadata=metadata)
    text = generate_display_size(layer)
    # the Source will not be set properly so even local zarr files will not
    # have a path set
    assert not layer.source.path
    assert 'in memory' in text


def test_directory_size(local_zarr_path):
    read_bytes = directory_size(local_zarr_path)
    expected_bytes = 1893

    assert pytest.approx(read_bytes, 100) == expected_bytes


@pytest.mark.parametrize(
    'size,text',
    (
        (13, '13.00 bytes'),
        (130, '130.00 bytes'),
        (1303, '1.30 KB'),
        (13031, '13.03 KB'),
        (130313, '130.31 KB'),
        (1303131, '1.30 MB'),
        (13031319, '13.03 MB'),
        (130313190, '130.31 MB'),
        (1303131900, '1.30 GB'),
    ),
)
def test_generate_text_for_size(size, text):
    assert generate_text_for_size(size) == text


def test_generate_text_for_size_with_suffix():
    size = 13
    suffix = ' (in memory)'
    text = generate_text_for_size(size, suffix=suffix)
    assert text == f'13.00 bytes{suffix}'


def test_no_path():
    layer = Image(np.zeros((5, 6)))
    text = generate_display_size(layer)
    # ensure layer does not have a path set
    assert not layer.source.path
    # if no source path, get in memory size
    assert 'in memory' in text
