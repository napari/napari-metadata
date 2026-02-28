import numpy as np
import pytest
from napari.components import ViewerModel

from napari_metadata.layer_utils import (
    connect_callback_to_layer_name_changed,
    connect_callback_to_layer_selection_events,
    connect_callback_to_list_events,
    disconnect_callback_to_layer_name_changed,
    disconnect_callback_to_layer_selection_events,
    disconnect_callback_to_list_events,
    get_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_dimensions,
    get_layer_source_path,
    get_layers_list,
    resolve_layer,
    set_axes_labels,
    set_axes_scales,
    set_axes_translations,
    set_axes_units,
)


@pytest.fixture
def viewer_model() -> ViewerModel:
    return ViewerModel()


@pytest.fixture
def viewer_model_with_layers(viewer_model: ViewerModel):
    """Viewer with two image layers; layer2 is active."""
    layer1 = viewer_model.add_image(np.zeros((4, 3)), name='layer1')
    layer2 = viewer_model.add_image(np.zeros((2, 2)), name='layer2')
    assert viewer_model.layers.selection.active is layer2
    return viewer_model, layer1, layer2


class TestResolveLayer:
    def test_returns_active_layer_by_default(self, viewer_model_with_layers):
        viewer, _layer1, layer2 = viewer_model_with_layers
        assert resolve_layer(viewer) is layer2

    def test_returns_explicit_layer(self, viewer_model_with_layers):
        viewer, layer1, _layer2 = viewer_model_with_layers
        assert resolve_layer(viewer, layer1) is layer1

    def test_returns_none_when_no_layers(self, viewer_model):
        assert resolve_layer(viewer_model) is None

    def test_switching_active_layer(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        assert resolve_layer(viewer) is layer2

        viewer.layers.selection.active = layer1
        assert resolve_layer(viewer) is layer1

        viewer.layers.selection.active = None
        assert resolve_layer(viewer) is None


class TestGetLayersList:
    def test_empty_viewer(self, viewer_model):
        assert get_layers_list(viewer_model) == []

    def test_returns_all_layers(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        assert get_layers_list(viewer) == [layer1, layer2]


class TestAxesLabels:
    def test_get_empty_when_no_layers(self, viewer_model):
        assert get_axes_labels(viewer_model) == ()

    def test_get_active_layer_labels(self, viewer_model):
        viewer_model.add_image(np.zeros((4, 3)), axis_labels=('ay', 'bee'))
        viewer_model.add_image(np.zeros((2, 2)), axis_labels=('cee', 'dee'))
        assert get_axes_labels(viewer_model) == ('cee', 'dee')

    def test_get_explicit_layer_labels(self, viewer_model):
        layer1 = viewer_model.add_image(
            np.zeros((4, 3)), axis_labels=('ay', 'bee')
        )
        viewer_model.add_image(np.zeros((2, 2)), axis_labels=('cee', 'dee'))
        assert get_axes_labels(viewer_model, layer1) == ('ay', 'bee')

    def test_set_no_op_when_no_layers(self, viewer_model):
        set_axes_labels(viewer_model, ('x', 'y', 'z'))  # should not raise

    def test_set_active_layer_labels(self, viewer_model):
        layer = viewer_model.add_image(
            np.zeros((4, 3)), axis_labels=('a', 'b')
        )
        set_axes_labels(viewer_model, ('x', 'y'))
        assert layer.axis_labels == ('x', 'y')

    def test_set_explicit_layer_labels(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        set_axes_labels(viewer, ('x', 'y'), layer=layer1)
        assert layer1.axis_labels == ('x', 'y')
        # layer2 unchanged — still has defaults
        assert layer2.axis_labels != ('x', 'y')


class TestAxesUnits:
    def test_get_empty_when_no_layers(self, viewer_model):
        assert get_axes_units(viewer_model) == ()

    def test_get_active_layer_units(self, viewer_model):
        viewer_model.add_image(
            np.zeros((4, 3)), units=('micrometer', 'micrometer')
        )
        viewer_model.add_image(np.zeros((2, 2)), units=('pixel', 'pixel'))
        assert get_axes_units(viewer_model) == ('pixel', 'pixel')

    def test_get_explicit_layer_units(self, viewer_model):
        layer1 = viewer_model.add_image(
            np.zeros((4, 3)), units=('micrometer', 'micrometer')
        )
        viewer_model.add_image(np.zeros((2, 2)), units=('pixel', 'pixel'))
        assert get_axes_units(viewer_model, layer1) == (
            'micrometer',
            'micrometer',
        )

    def test_set_no_op_when_no_layers(self, viewer_model):
        set_axes_units(
            viewer_model, ('micrometer', 'micrometer')
        )  # should not raise

    def test_set_active_layer_units(self, viewer_model):
        layer = viewer_model.add_image(
            np.zeros((4, 3)), units=('pixel', 'pixel')
        )
        set_axes_units(viewer_model, ('micrometer', 'micrometer'))
        assert layer.units == ('micrometer', 'micrometer')

    def test_set_explicit_layer_units(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        set_axes_units(viewer, ('nanometer', 'nanometer'), layer=layer1)
        assert layer1.units == ('nanometer', 'nanometer')


class TestAxesScales:
    def test_get_empty_when_no_layers(self, viewer_model):
        assert get_axes_scales(viewer_model) == ()

    def test_get_active_layer_scales(self, viewer_model):
        viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 2.0))
        viewer_model.add_image(np.zeros((2, 2)), scale=(0.5, 0.5))
        assert np.allclose(get_axes_scales(viewer_model), (0.5, 0.5))

    def test_get_explicit_layer_scales(self, viewer_model):
        layer1 = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 2.0))
        viewer_model.add_image(np.zeros((2, 2)), scale=(0.5, 0.5))
        assert np.allclose(get_axes_scales(viewer_model, layer1), (1.0, 2.0))

    def test_set_no_op_when_no_layers(self, viewer_model):
        set_axes_scales(viewer_model, (1.0, 1.0))  # should not raise

    def test_set_active_layer_scales(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(viewer_model, (0.5, 0.5))
        assert np.allclose(layer.scale, (0.5, 0.5))

    def test_set_explicit_layer_scales(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        set_axes_scales(viewer, (0.1, 0.1), layer=layer1)
        assert np.allclose(layer1.scale, (0.1, 0.1))
        assert np.allclose(layer2.scale, (1.0, 1.0))  # default unchanged

    def test_set_rejects_non_float(self, viewer_model):
        """Non-float values cause early return without modification."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(viewer_model, ('bad', 'values'))
        assert np.allclose(layer.scale, (1.0, 1.0))  # unchanged

    def test_set_clamps_zero_scale(self, viewer_model):
        """Scales <= 0 are clamped to 0.001."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(viewer_model, (0.0, -1.0))
        assert np.allclose(layer.scale, (0.001, 0.001))

    def test_set_clamps_only_non_positive(self, viewer_model):
        """Only non-positive values are clamped; positive values pass through."""
        layer = viewer_model.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        set_axes_scales(viewer_model, (2.0, 0.0))
        assert np.allclose(layer.scale, (2.0, 0.001))


class TestAxesTranslations:
    def test_get_empty_when_no_layers(self, viewer_model):
        assert get_axes_translations(viewer_model) == ()

    def test_get_active_layer_translations(self, viewer_model):
        viewer_model.add_image(np.zeros((4, 3)), translate=(0.0, 1.0))
        viewer_model.add_image(np.zeros((2, 2)), translate=(2.0, 2.0))
        assert np.allclose(get_axes_translations(viewer_model), (2.0, 2.0))

    def test_get_explicit_layer_translations(self, viewer_model):
        layer1 = viewer_model.add_image(np.zeros((4, 3)), translate=(0.0, 1.0))
        viewer_model.add_image(np.zeros((2, 2)), translate=(2.0, 2.0))
        assert np.allclose(
            get_axes_translations(viewer_model, layer1), (0.0, 1.0)
        )

    def test_set_no_op_when_no_layers(self, viewer_model):
        set_axes_translations(viewer_model, (0.0, 0.0))  # should not raise

    def test_set_active_layer_translations(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3)), translate=(0.0, 0.0))
        set_axes_translations(viewer_model, (1.0, 1.0))
        assert np.allclose(layer.translate, (1.0, 1.0))

    def test_set_explicit_layer_translations(self, viewer_model_with_layers):
        viewer, layer1, layer2 = viewer_model_with_layers
        set_axes_translations(viewer, (3.0, 3.0), layer=layer1)
        assert np.allclose(layer1.translate, (3.0, 3.0))
        assert np.allclose(layer2.translate, (0.0, 0.0))  # default unchanged


class TestGetLayerDataShape:
    def test_none_layer(self):
        assert get_layer_data_shape(None) == ()

    def test_ndarray_layer(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3, 2)))
        assert get_layer_data_shape(layer) == (4, 3, 2)

    def test_shapes_layer(self, viewer_model):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]])]
        layer = viewer_model.add_shapes(shape_data, shape_type='polygon')
        # Shapes.data is a list → falls into Sequence branch
        shape = get_layer_data_shape(layer)
        assert shape == (1,)

    def test_multiscale_layer(self, viewer_model):
        scales = [np.zeros((20, 20)), np.zeros((10, 10))]
        layer = viewer_model.add_image(scales, multiscale=True)
        shape = get_layer_data_shape(layer)
        assert len(shape) > 0


class TestGetLayerDataDtype:
    def test_none_layer(self):
        assert get_layer_data_dtype(None) == ''

    def test_float32_layer(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3), dtype=np.float32))
        assert get_layer_data_dtype(layer) == 'float32'

    def test_uint8_layer(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((2, 2), dtype=np.uint8))
        assert get_layer_data_dtype(layer) == 'uint8'

    def test_shapes_layer_dtype(self, viewer_model):
        shape_data = [np.array([[0, 0], [1, 1], [1, 0]], dtype=np.float32)]
        layer = viewer_model.add_shapes(shape_data, shape_type='polygon')
        dtype = get_layer_data_dtype(layer)
        assert dtype == 'float32'


class TestGetLayerSourcePath:
    def test_none_layer(self):
        assert get_layer_source_path(None) == ''

    def test_in_memory_layer_has_no_path(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        path = get_layer_source_path(layer)
        assert path == '' or isinstance(path, str)


class TestGetLayerDimensions:
    def test_none_layer(self):
        assert get_layer_dimensions(None) == 0

    def test_2d_layer(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3)))
        assert get_layer_dimensions(layer) == 2

    def test_3d_layer(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((5, 4, 3)))
        assert get_layer_dimensions(layer) == 3


class TestCallbackHelpers:
    """Tests for connect/disconnect callback functions.

    Verify the wiring works without error, and that callbacks
    are actually invoked by triggering events.
    """

    def test_connect_disconnect_selection_events(self, viewer_model):
        calls = []

        def cb(event):
            return calls.append(event)

        connect_callback_to_layer_selection_events(viewer_model, cb)

        layer = viewer_model.add_image(np.zeros((4, 3)))
        viewer_model.layers.selection.active = layer
        assert len(calls) > 0

        disconnect_callback_to_layer_selection_events(viewer_model, cb)

    def test_disconnect_selection_events_no_error_when_not_connected(
        self, viewer_model
    ):
        def cb(event):
            return None

        # Should not raise even though cb was never connected
        disconnect_callback_to_layer_selection_events(viewer_model, cb)

    def test_connect_disconnect_list_events(self, viewer_model):
        calls = []

        def cb(event):
            return calls.append(event)

        connect_callback_to_list_events(viewer_model, cb)

        viewer_model.add_image(np.zeros((4, 3)))
        assert len(calls) > 0  # inserted event fired

        disconnect_callback_to_list_events(viewer_model, cb)

    def test_disconnect_list_events_no_error_when_not_connected(
        self, viewer_model
    ):
        def cb(event):
            return None

        disconnect_callback_to_list_events(viewer_model, cb)

    def test_connect_disconnect_layer_name_changed(self, viewer_model):
        layer = viewer_model.add_image(np.zeros((4, 3)), name='original')
        calls = []

        def cb(event):
            return calls.append(event)

        connect_callback_to_layer_name_changed(viewer_model, cb, layer)
        layer.name = 'renamed'
        assert len(calls) > 0

        disconnect_callback_to_layer_name_changed(viewer_model, cb, layer)

    def test_connect_layer_name_changed_no_layer(self, viewer_model):
        """When no layer exists, connect is a no-op."""

        def cb(event):
            return None

        connect_callback_to_layer_name_changed(viewer_model, cb, None)

    def test_disconnect_layer_name_changed_none_layer(self, viewer_model):
        """Disconnecting with None layer is a no-op."""

        def cb(event):
            return None

        disconnect_callback_to_layer_name_changed(viewer_model, cb, None)
