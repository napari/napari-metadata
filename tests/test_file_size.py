"""Tests for napari_metadata._file_size."""

import os
from unittest.mock import MagicMock

import napari.layers
import numpy as np
import pytest

from napari_metadata._file_size import (
    directory_size,
    generate_display_size,
    generate_text_for_size,
)


class TestGenerateTextForSize:
    def test_zero_bytes(self):
        assert generate_text_for_size(0) == '0.00 bytes'

    def test_small_bytes(self):
        assert generate_text_for_size(13) == '13.00 bytes'

    def test_upper_byte_boundary(self):
        # order == 2 (999 bytes) → still bytes
        assert generate_text_for_size(999) == '999.00 bytes'

    def test_kilobytes(self):
        assert generate_text_for_size(1_000) == '1.00 KB'
        assert generate_text_for_size(1_500) == '1.50 KB'

    def test_megabytes(self):
        assert generate_text_for_size(1_000_000) == '1.00 MB'
        assert generate_text_for_size(1_303_131) == '1.30 MB'

    def test_gigabytes(self):
        assert generate_text_for_size(1_000_000_000) == '1.00 GB'

    def test_suffix_appended(self):
        result = generate_text_for_size(1_303_131, suffix=' (in memory)')
        assert result == '1.30 MB (in memory)'

    def test_suffix_empty_string_default(self):
        result = generate_text_for_size(100)
        assert '(in memory)' not in result


class TestGenerateDisplaySize:
    def test_in_memory_image(self):
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert result == generate_text_for_size(data.nbytes, suffix=' (in memory)')

    def test_in_memory_multiscale_image(self):
        scales = [np.zeros((20, 20), dtype=np.uint8), np.zeros((10, 10), dtype=np.uint8)]
        layer = napari.layers.Image(scales, multiscale=True)
        expected_size = sum(s.nbytes for s in scales)
        result = generate_display_size(layer)
        assert result == generate_text_for_size(expected_size, suffix=' (in memory)')

    def test_in_memory_shapes(self):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = napari.layers.Shapes(shape_data, shape_type='polygon')
        expected_size = sum(d.nbytes for d in layer.data)
        result = generate_display_size(layer)
        assert result == generate_text_for_size(expected_size, suffix=' (in memory)')

    def test_in_memory_surface(self):
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        layer = napari.layers.Surface((vertices, faces))
        expected_size = sum(d.nbytes for d in layer.data)
        result = generate_display_size(layer)
        assert result == generate_text_for_size(expected_size, suffix=' (in memory)')

    def test_from_disk_path(self, tmp_path):
        data = np.zeros((10, 10), dtype=np.uint8)
        file_path = tmp_path / 'test.npy'
        np.save(file_path, data)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(file_path)
        result = generate_display_size(layer)
        expected_size = os.path.getsize(str(file_path))
        assert result == generate_text_for_size(expected_size)
        assert '(in memory)' not in result

    def test_in_memory_suffix_present(self):
        # data is not on disk, so in memory will be appended
        data = np.zeros((4, 4), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert '(in memory)' in result

    def test_from_disk_no_in_memory_suffix(self, tmp_path):
        data = np.zeros((4, 4), dtype=np.uint8)
        file_path = tmp_path / 'test.npy'
        np.save(file_path, data)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(file_path)
        result = generate_display_size(layer)
        assert '(in memory)' not in result


class TestDirectorySize:
    def test_returns_total_size(self, tmp_path):
        file1 = tmp_path / 'a.txt'
        file2 = tmp_path / 'b.txt'
        file1.write_bytes(b'hello')   # 5 bytes
        file2.write_bytes(b'world!')  # 6 bytes
        assert directory_size(tmp_path) == 11

    def test_nested_directory(self, tmp_path):
        sub = tmp_path / 'sub'
        sub.mkdir()
        (tmp_path / 'root.txt').write_bytes(b'abc')  # 3 bytes
        (sub / 'child.txt').write_bytes(b'de')       # 2 bytes
        assert directory_size(tmp_path) == 5

    def test_empty_directory(self, tmp_path):
        assert directory_size(tmp_path) == 0

    def test_accepts_string_path(self, tmp_path):
        (tmp_path / 'f.txt').write_bytes(b'x')
        assert directory_size(str(tmp_path)) == 1

    def test_raises_for_non_directory(self, tmp_path):
        file = tmp_path / 'file.txt'
        file.write_bytes(b'data')
        with pytest.raises(RuntimeError, match='not a directory'):
            directory_size(file)
