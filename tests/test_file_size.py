"""Tests for napari_metadata.file_size."""

import os
from unittest.mock import MagicMock

import napari.layers
import numpy as np
import pytest

from napari_metadata.file_size import (
    _generate_text_for_size,
    _get_napari_size,
    _get_stored_size,
    _has_lazy_data,
    _is_lazy_data,
    _is_remote_path,
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


class TestIsRemotePath:
    def test_none_is_not_remote(self):
        assert _is_remote_path(None) is False

    def test_empty_string_is_not_remote(self):
        assert _is_remote_path('') is False

    def test_http_is_remote(self):
        assert _is_remote_path('http://example.com/data.zarr') is True

    def test_https_is_remote(self):
        assert _is_remote_path('https://example.com/data.zarr') is True

    def test_s3_is_remote(self):
        assert _is_remote_path('s3://bucket/data.zarr') is True

    def test_gcs_is_remote(self):
        assert _is_remote_path('gs://bucket/data.zarr') is True

    def test_abfs_is_remote(self):
        assert _is_remote_path('abfs://container/data.zarr') is True

    def test_ftp_is_remote(self):
        assert _is_remote_path('ftp://example.com/data.zarr') is True

    def test_windows_drive_is_not_remote(self):
        assert _is_remote_path('C:\\Users\\user\\data.tif') is False

    def test_unix_absolute_path_is_not_remote(self):
        assert _is_remote_path('/home/user/data.tif') is False

    def test_file_scheme_is_not_remote(self):
        assert _is_remote_path('file:///home/user/data.tif') is False

    def test_relative_path_is_not_remote(self):
        assert _is_remote_path('data/test.tif') is False


class TestIsLazyData:
    def test_numpy_array_is_not_lazy(self):
        assert _is_lazy_data(np.zeros((5, 5))) is False

    def test_dask_array_is_lazy(self):
        dask = pytest.importorskip('dask.array')
        assert _is_lazy_data(dask.zeros((5, 5))) is True

    def test_list_is_not_lazy(self):
        assert _is_lazy_data([1, 2, 3]) is False

    def test_none_is_not_lazy(self):
        assert _is_lazy_data(None) is False


class TestHasLazyData:
    def test_numpy_image_is_not_lazy(self):
        layer = napari.layers.Image(np.zeros((10, 10), dtype=np.uint8))
        assert _has_lazy_data(layer) is False

    def test_dask_image_is_lazy(self):
        dask = pytest.importorskip('dask.array')
        layer = napari.layers.Image(dask.zeros((10, 10), dtype=np.uint8))
        assert _has_lazy_data(layer) is True

    def test_multiscale_numpy_is_not_lazy(self):
        scales = [np.zeros((20, 20)), np.zeros((10, 10))]
        layer = napari.layers.Image(scales, multiscale=True)
        assert _has_lazy_data(layer) is False

    def test_multiscale_dask_is_lazy(self):
        dask = pytest.importorskip('dask.array')
        scales = [dask.zeros((20, 20)), dask.zeros((10, 10))]
        layer = napari.layers.Image(scales, multiscale=True)
        assert _has_lazy_data(layer) is True


class TestGetStoredSize:
    def test_single_file(self, tmp_path):
        f = tmp_path / 'test.npy'
        np.save(f, np.zeros((10, 10), dtype=np.uint8))
        assert _get_stored_size(str(f)) == f.stat().st_size

    def test_directory(self, tmp_path):
        d = tmp_path / 'data'
        d.mkdir()
        f1 = d / 'a.npy'
        f2 = d / 'b.npy'
        np.save(f1, np.zeros((10, 10), dtype=np.uint8))
        np.save(f2, np.zeros((10, 10), dtype=np.uint8))
        expected = f1.stat().st_size + f2.stat().st_size
        assert _get_stored_size(str(d)) == expected

    def test_nested_directory(self, tmp_path):
        d = tmp_path / 'data'
        sub = d / 'sub'
        sub.mkdir(parents=True)
        f1 = d / 'a.npy'
        f2 = sub / 'b.npy'
        np.save(f1, np.zeros((10, 10), dtype=np.uint8))
        np.save(f2, np.zeros((10, 10), dtype=np.uint8))
        expected = f1.stat().st_size + f2.stat().st_size
        assert _get_stored_size(str(d)) == expected

    def test_nonexistent_path_returns_none(self, tmp_path):
        assert _get_stored_size(str(tmp_path / 'nonexistent.tif')) is None


class TestGetNapariSize:
    def test_simple_image(self):
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = napari.layers.Image(data)
        assert _get_napari_size(layer) == data.nbytes

    def test_uint32_image(self):
        data = np.zeros((10, 10), dtype=np.uint32)
        layer = napari.layers.Image(data)
        assert _get_napari_size(layer) == data.nbytes

    def test_multiscale_image_sums_all_scales(self):
        scales = [
            np.zeros((20, 20), dtype=np.uint8),
            np.zeros((10, 10), dtype=np.uint8),
        ]
        layer = napari.layers.Image(scales, multiscale=True)
        assert _get_napari_size(layer) == sum(s.nbytes for s in scales)

    def test_shapes_layer(self):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = napari.layers.Shapes(shape_data, shape_type='polygon')
        assert _get_napari_size(layer) == sum(d.nbytes for d in layer.data)

    def test_surface_layer(self):
        vertices = np.array(
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32
        )
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        layer = napari.layers.Surface((vertices, faces))
        assert _get_napari_size(layer) == sum(d.nbytes for d in layer.data)

    def test_dask_image_reports_theoretical_size(self):
        dask = pytest.importorskip('dask.array')
        data = dask.zeros((100, 100), dtype=np.uint32, chunks=(50, 50))
        layer = napari.layers.Image(data)
        assert _get_napari_size(layer) == data.nbytes


class TestGenerateDisplaySize:
    # ── In-memory layers ────────────────────────────────────────────────────

    def test_in_memory_image_shows_in_memory_suffix(self):
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(data.nbytes, ' (in memory)')

    def test_in_memory_multiscale_shows_in_memory_suffix(self):
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

    def test_in_memory_suffix_present(self):
        data = np.zeros((4, 4), dtype=np.uint8)
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert '(in memory)' in result
        assert '(on disk)' not in result

    def test_in_memory_dask_shows_lazy_suffix(self):
        dask = pytest.importorskip('dask.array')
        data = dask.zeros((50, 50), dtype=np.uint8, chunks=(25, 25))
        layer = napari.layers.Image(data)
        result = generate_display_size(layer)
        assert '(uncompressed, lazy)' in result
        assert '(in memory)' not in result
        assert '(on disk)' not in result

    # ── Local file/directory layers ─────────────────────────────────────────

    def test_from_disk_single_file_shows_both_sizes(self, tmp_path):
        data = np.zeros((10, 10), dtype=np.uint8)
        file_path = tmp_path / 'test.npy'
        np.save(file_path, data)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(file_path)
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        stored_size = os.path.getsize(str(file_path))
        assert _generate_text_for_size(stored_size, ' (on disk)') in result
        assert (
            _generate_text_for_size(data.nbytes, ' (uncompressed)') in result
        )
        assert '(in memory)' not in result
        assert '(lazy)' not in result

    def test_from_disk_directory_shows_both_sizes(self, tmp_path):
        dir_path = tmp_path / 'test_dir'
        dir_path.mkdir()
        f1 = dir_path / 'a.npy'
        f2 = dir_path / 'b.npy'
        data1 = np.zeros((10, 10), dtype=np.uint8)
        data2 = np.zeros((20, 20), dtype=np.uint8)
        np.save(f1, data1)
        np.save(f2, data2)
        combined = np.concatenate([data1.ravel(), data2.ravel()])
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(dir_path)
        layer.data = combined
        layer.multiscale = False
        result = generate_display_size(layer)
        stored_size = os.path.getsize(str(f1)) + os.path.getsize(str(f2))
        assert _generate_text_for_size(stored_size, ' (on disk)') in result
        assert '(in memory)' not in result

    def test_from_disk_directory_with_subdirectory(self, tmp_path):
        dir_path = tmp_path / 'test_dir'
        dir_path.mkdir()
        sub_dir = dir_path / 'sub_dir'
        sub_dir.mkdir()
        f1 = dir_path / 'a.npy'
        f2 = sub_dir / 'b.npy'
        np.save(f1, np.zeros((10, 10), dtype=np.uint8))
        np.save(f2, np.zeros((20, 20), dtype=np.uint8))
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(dir_path)
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        stored_size = os.path.getsize(str(f1)) + os.path.getsize(str(f2))
        assert _generate_text_for_size(stored_size, ' (on disk)') in result

    def test_from_disk_lazy_dask_shows_lazy_suffix(self, tmp_path):
        """Local zarr-like directory opened as dask array shows both sizes."""
        dask = pytest.importorskip('dask.array')
        dir_path = tmp_path / 'zarr_store'
        dir_path.mkdir()
        f = dir_path / 'chunk.npy'
        np.save(f, np.zeros((10, 10), dtype=np.uint32))
        data = dask.zeros((100, 100), dtype=np.uint32, chunks=(50, 50))
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = str(dir_path)
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        assert '(on disk)' in result
        assert '(uncompressed, lazy)' in result
        assert '(in memory)' not in result

    # ── Remote layers ────────────────────────────────────────────────────────

    def test_remote_https_numpy_shows_uncompressed(self):
        data = np.zeros((10, 10), dtype=np.uint8)
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = 'https://example.com/data.zarr'
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        assert result == _generate_text_for_size(
            data.nbytes, ' (uncompressed)'
        )
        assert '(in memory)' not in result
        assert '(on disk)' not in result

    def test_remote_https_dask_shows_lazy_suffix(self):
        """This is the case from issue #140: remote zarr must not say 'in memory'."""
        dask = pytest.importorskip('dask.array')
        data = dask.zeros(
            (1000, 1000, 100), dtype=np.uint16, chunks=(100, 100, 10)
        )
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = 'https://example.com/ome.zarr'
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        assert '(uncompressed, lazy)' in result
        assert '(in memory)' not in result
        assert '(on disk)' not in result

    def test_remote_s3_dask_shows_lazy_suffix(self):
        dask = pytest.importorskip('dask.array')
        data = dask.zeros((50, 50), dtype=np.float32, chunks=(25, 25))
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = 's3://my-bucket/data.zarr'
        layer.data = data
        layer.multiscale = False
        result = generate_display_size(layer)
        assert '(uncompressed, lazy)' in result
        assert '(in memory)' not in result
        assert '(on disk)' not in result

    def test_remote_multiscale_dask_shows_lazy_suffix(self):
        """Multiscale remote zarr (napari-ome-zarr use case) — issue #140."""
        dask = pytest.importorskip('dask.array')
        scales = [
            dask.zeros((200, 200), dtype=np.uint16, chunks=(100, 100)),
            dask.zeros((100, 100), dtype=np.uint16, chunks=(50, 50)),
        ]
        layer = MagicMock(spec=napari.layers.Image)
        layer.source.path = 'https://example.com/ome.zarr'
        layer.data = scales
        layer.multiscale = True
        result = generate_display_size(layer)
        assert '(uncompressed, lazy)' in result
        assert '(in memory)' not in result
        assert '(on disk)' not in result
