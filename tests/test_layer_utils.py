from typing import Any

import numpy as np
import pytest
from napari.components import ViewerModel
from napari.layers import Image

from napari_metadata.layer_utils import (
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_source_path,
    set_axes_scales,
)


@pytest.fixture
def viewer_model() -> ViewerModel:
    return ViewerModel()


class TestSetAxesScales:
    def test_set_scales_on_layer(self, viewer_model: ViewerModel):
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(layer, (0.5, 0.5))
        assert np.allclose(layer.scale, (0.5, 0.5))

    def test_set_rejects_non_numeric(self, viewer_model: ViewerModel):
        """Non-numeric values cause early return without modification."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        bad_values: Any = ('bad', 'values')
        set_axes_scales(layer, bad_values)
        assert np.allclose(layer.scale, (1.0, 1.0))  # unchanged

    def test_set_accepts_int(self, viewer_model: ViewerModel):
        """Integer scale values are accepted and applied."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(layer, (2, 3))
        assert np.allclose(layer.scale, (2.0, 3.0))

    def test_set_clamps_zero_scale(self, viewer_model: ViewerModel):
        """Scales <= 0 are clamped to 0.001."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(layer, (0.0, -1.0))
        assert np.allclose(layer.scale, (0.001, 0.001))

    def test_set_clamps_only_non_positive(self, viewer_model: ViewerModel):
        """Only non-positive values are clamped; positive values pass through."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(layer, (2.0, 0.0))
        assert np.allclose(layer.scale, (2.0, 0.001))

    def test_standalone_layer(self):
        """Works with a standalone layer (no viewer)."""
        layer = Image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(layer, (0.5, 0.5))
        assert np.allclose(layer.scale, (0.5, 0.5))


class TestGetLayerDataShape:
    def test_ndarray_layer(self, viewer_model: ViewerModel):
        layer = viewer_model.add_image(np.zeros((4, 3, 2)))
        assert get_layer_data_shape(layer) == (4, 3, 2)

    def test_shapes_layer(self, viewer_model: ViewerModel):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]])]
        layer = viewer_model.add_shapes(shape_data, shape_type='polygon')
        shape = get_layer_data_shape(layer)
        assert shape == (1,)

    def test_multiscale_layer(self, viewer_model: ViewerModel):
        scales = [np.zeros((20, 20)), np.zeros((10, 10))]
        layer = viewer_model.add_image(scales, multiscale=True)
        shape = get_layer_data_shape(layer)
        assert len(shape) > 0

    def test_standalone_layer(self):
        layer = Image(np.zeros((5, 4)))
        assert get_layer_data_shape(layer) == (5, 4)


class TestGetLayerDataDtype:
    def test_float32_layer(self, viewer_model: ViewerModel):
        layer = viewer_model.add_image(np.zeros((4, 3), dtype=np.float32))
        assert get_layer_data_dtype(layer) == 'float32'

    def test_uint8_layer(self, viewer_model: ViewerModel):
        layer = viewer_model.add_image(np.zeros((2, 2), dtype=np.uint8))
        assert get_layer_data_dtype(layer) == 'uint8'

    def test_shapes_layer_dtype(self, viewer_model: ViewerModel):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = viewer_model.add_shapes(shape_data, shape_type='polygon')
        dtype = get_layer_data_dtype(layer)
        assert dtype == 'float32'

    def test_non_native_endian_dtype_is_human_readable(
        self, viewer_model: ViewerModel
    ):
        """Non-native endian dtype like '>u2' should display as 'uint16', not '>u2'."""
        data = np.zeros((4, 4), dtype=np.dtype('>u2'))
        layer = viewer_model.add_image(data)
        assert get_layer_data_dtype(layer) == 'uint16'

    def test_little_endian_float64_is_human_readable(
        self, viewer_model: ViewerModel
    ):
        """Little-endian dtype '<f8' should display as 'float64'."""
        data = np.zeros((3, 3), dtype=np.dtype('<f8'))
        layer = viewer_model.add_image(data)
        assert get_layer_data_dtype(layer) == 'float64'

    def test_standalone_layer(self):
        layer = Image(np.zeros((3, 3), dtype=np.int32))
        assert get_layer_data_dtype(layer) == 'int32'


class TestGetLayerSourcePath:
    def test_in_memory_layer_has_no_path(self, viewer_model: ViewerModel):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        path = get_layer_source_path(layer)
        assert path == '' or isinstance(path, str)

    def test_standalone_layer(self):
        layer = Image(np.zeros((4, 3)))
        assert get_layer_source_path(layer) == ''
