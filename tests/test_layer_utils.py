import numpy as np
from napari.layers import Image, Shapes

from napari_metadata.layer_utils import (
    get_layer_data_dtype,
    get_layer_data_shape,
)


class TestGetLayerDataShape:
    def test_ndarray_layer(self):
        layer = Image(np.zeros((4, 3, 2)))
        assert get_layer_data_shape(layer) == (4, 3, 2)

    def test_shapes_layer(self):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]])]
        layer = Shapes(shape_data, shape_type='polygon')
        shape = get_layer_data_shape(layer)
        assert shape == (1,)

    def test_multiscale_layer(self):
        scales = [np.zeros((20, 20)), np.zeros((10, 10))]
        layer = Image(scales, multiscale=True)
        shape = get_layer_data_shape(layer)
        # MultiScaleData exposes .shape of the highest-resolution level
        assert shape == (20, 20)

    def test_standalone_layer(self):
        layer = Image(np.zeros((5, 4)))
        assert get_layer_data_shape(layer) == (5, 4)


class TestGetLayerDataDtype:
    def test_float32_layer(self):
        layer = Image(np.zeros((4, 3), dtype=np.float32))
        assert get_layer_data_dtype(layer) == 'float32'

    def test_uint8_layer(self):
        layer = Image(np.zeros((2, 2), dtype=np.uint8))
        assert get_layer_data_dtype(layer) == 'uint8'

    def test_shapes_layer_dtype(self):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = Shapes(shape_data, shape_type='polygon')
        dtype = get_layer_data_dtype(layer)
        assert dtype == 'float32'

    def test_non_native_endian_dtype_is_human_readable(self):
        """Non-native endian dtype like '>u2' should display as 'uint16', not '>u2'."""
        data = np.zeros((4, 4), dtype=np.dtype('>u2'))
        layer = Image(data)
        assert get_layer_data_dtype(layer) == 'uint16'

    def test_little_endian_float64_is_human_readable(self):
        """Little-endian dtype '<f8' should display as 'float64'."""
        data = np.zeros((3, 3), dtype=np.dtype('<f8'))
        layer = Image(data)
        assert get_layer_data_dtype(layer) == 'float64'

    def test_standalone_layer(self):
        layer = Image(np.zeros((3, 3), dtype=np.int32))
        assert get_layer_data_dtype(layer) == 'int32'
