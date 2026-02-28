"""Tests for napari_metadata.file_size."""

import os
from unittest.mock import MagicMock

import napari.layers
import numpy as np

from napari_metadata.file_size import (
    _generate_text_for_size,
    generate_display_size,
)


class TestGenerateTextForSize:
    def test_zero_bytes(self):
        assert _generate_text_for_size(0) == '0.00 bytes'

    def test_small_bytes(self):
        assert _generate_text_for_size(13) == '13.00 bytes'

    def test_upper_byte_boundary(self):
        # order == 2 (999 bytes) → still bytes
        assert _generate_text_for_size(999) == '999.00 bytes'

    def test_kilobytes(self):
        assert _generate_text_for_size(1_000) == '1.00 KB'
        assert _generate_text_for_size(1_500) == '1.50 KB'

    def test_megabytes(self):
        assert _generate_text_for_size(1_000_000) == '1.00 MB'
        assert _generate_text_for_size(1_303_131) == '1.30 MB'

    def test_gigabytes(self):
        assert _generate_text_for_size(1_000_000_000) == '1.00 GB'

    def test_suffix_appended(self):
        result = _generate_text_for_size(1_303_131, suffix=' (in memory)')
        assert result == '1.30 MB (in memory)'

    def test_suffix_empty_string_default(self):
        result = _generate_text_for_size(100)
        assert '(in memory)' not in result


class TestGenerateDisplaySize:
    def test_in_memory_image(self):
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(
            data.nbytes, suffix=' (in memory)'
        )

    def test_in_memory_multiscale_image(self):
        scales = [
            np.zeros((20, 20), dtype=np.uint8),
            np.zeros((10, 10), dtype=np.uint8),
        ]
        layer = napari.layers.Image(scales, multiscale=True)
        expected_size = sum(s.nbytes for s in scales)
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(
            expected_size, suffix=' (in memory)'
        )

    def test_in_memory_shapes(self):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = napari.layers.Shapes(shape_data, shape_type='polygon')
        expected_size = sum(d.nbytes for d in layer.data)
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(
            expected_size, suffix=' (in memory)'
        )

    def test_in_memory_surface(self):
        vertices = np.array(
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32
        )
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        layer = napari.layers.Surface((vertices, faces))
        expected_size = sum(d.nbytes for d in layer.data)
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(
            expected_size, suffix=' (in memory)'
        )

    def test_from_disk_path(self, tmp_path):
        data = np.zeros((10, 10), dtype=np.uint8)
        file_path = tmp_path / 'test.npy'
        np.save(file_path, data)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(file_path)
        result = generate_display_size(layer)
        expected_size = os.path.getsize(str(file_path))
        assert result == _generate_text_for_size(expected_size)
        assert '(in memory)' not in result

    def test_from_disk_directory(self, tmp_path):
        dir_path = tmp_path / 'test_dir'
        dir_path.mkdir()
        file1 = dir_path / 'a.npy'
        file2 = dir_path / 'b.npy'
        np.save(file1, np.zeros((10, 10), dtype=np.uint8))
        np.save(file2, np.zeros((20, 20), dtype=np.uint8))
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(dir_path)
        result = generate_display_size(layer)
        expected_size = os.path.getsize(str(file1)) + os.path.getsize(
            str(file2)
        )
        assert result == _generate_text_for_size(expected_size)
        assert '(in memory)' not in result

    def test_from_disk_directory_with_subdirectory(self, tmp_path):
        dir_path = tmp_path / 'test_dir'
        dir_path.mkdir()
        sub_dir = dir_path / 'sub_dir'
        sub_dir.mkdir()
        file1 = dir_path / 'a.npy'
        file2 = sub_dir / 'b.npy'
        np.save(file1, np.zeros((10, 10), dtype=np.uint8))
        np.save(file2, np.zeros((20, 20), dtype=np.uint8))
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(dir_path)
        result = generate_display_size(layer)
        expected_size = os.path.getsize(str(file1)) + os.path.getsize(
            str(file2)
        )
        assert result == _generate_text_for_size(expected_size)
        assert '(in memory)' not in result

    def test_in_memory_suffix_present(self):
        # data is not on disk, so in memory will be appended
        data = np.zeros((4, 4), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert '(in memory)' in result
