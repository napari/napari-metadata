import numpy as np
from napari.components import ViewerModel

from napari_metadata._model import (
    get_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_dimensions,
    get_layer_source_path,
    get_layers_list,
    get_pint_ureg,
    resolve_layer,
    set_axes_labels,
    set_axes_scales,
    set_axes_translations,
    set_axes_units,
)


class TestResolveLayer:
    def test_resolve_layer_active(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)))
        layer2 = viewer.add_image(np.zeros((2, 2)))

        assert viewer.layers.selection.active is layer2

        resolved_layer = resolve_layer(viewer)
        assert resolved_layer is layer2

        viewer.layers.selection.active = layer1
        resolved_layer = resolve_layer(viewer)
        assert resolved_layer is layer1

        viewer.layers.selection.active = None
        resolved_layer = resolve_layer(viewer)
        assert resolved_layer is None

    def test_resolve_layer_explicit(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)))
        layer2 = viewer.add_image(np.zeros((2, 2)))

        resolved_layer = resolve_layer(viewer, layer1)
        assert resolved_layer is layer1

        resolved_layer = resolve_layer(viewer, layer2)
        assert resolved_layer is layer2


class TestGetLayersList:
    def test_get_layers_list_empty(self):
        viewer = ViewerModel()
        layers = get_layers_list(viewer)
        assert layers == []

    def test_get_layers_list_non_empty(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)))
        layer2 = viewer.add_image(np.zeros((2, 2)))

        layers = get_layers_list(viewer)
        assert layers == [layer1, layer2]


class TestGetAxesLabels:
    def test_get_axes_labels_no_active_layer(self):
        viewer = ViewerModel()
        labels = get_axes_labels(viewer)
        assert labels == ()

    def test_get_axes_labels_active_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), axis_labels=('ay', 'bee'))
        layer2 = viewer.add_image(np.zeros((2, 2)), axis_labels=('cee', 'dee'))

        assert viewer.layers.selection.active is layer2
        labels = get_axes_labels(viewer)
        assert labels == ('cee', 'dee')

        viewer.layers.selection.active = layer1
        labels = get_axes_labels(viewer)
        assert labels == ('ay', 'bee')


class TestSetAxesLabels:
    def test_set_axes_labels_no_active_layer(self):
        viewer = ViewerModel()
        # should not raise error
        set_axes_labels(viewer, ('x', 'y', 'z'))

    def test_set_axes_labels_active_layer(self):
        viewer = ViewerModel()
        layer = viewer.add_image(np.zeros((4, 3)), axis_labels=('a', 'b'))

        assert viewer.layers.selection.active is layer

        set_axes_labels(viewer, ('x', 'y'))
        assert layer.axis_labels == ('x', 'y')

    def test_set_axes_labels_explicit_layer(self):
        """Test that explicit layer parameter is used, not active layer."""
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), axis_labels=('a', 'b'))
        layer2 = viewer.add_image(np.zeros((5, 6)), axis_labels=('c', 'd'))

        # layer2 is active but we modify layer1 explicitly
        assert viewer.layers.selection.active is layer2
        set_axes_labels(viewer, ('x', 'y'), layer=layer1)

        assert layer1.axis_labels == ('x', 'y')
        assert layer2.axis_labels == ('c', 'd')  # unchanged


class TestGetPintUreg:
    def test_get_pint_ureg_no_active_layer(self):
        viewer = ViewerModel()
        ureg = get_pint_ureg(viewer)
        assert ureg is None

    def test_get_pint_ureg_active_layer_default_units(self):
        """napari defaults to 'pixels' units which get converted to pint Units."""
        viewer = ViewerModel()
        layer = viewer.add_image(np.zeros((4, 3)))
        assert viewer.layers.selection.active is layer

        ureg = get_pint_ureg(viewer)
        # napari's default 'pixels' units are converted to pint Units
        assert ureg is not None
        assert hasattr(ureg, 'pixel')  # verify it's a valid pint registry

    def test_get_pint_ureg_active_layer_with_units(self):
        viewer = ViewerModel()
        layer = viewer.add_image(
            np.zeros((4, 3)), units=('micrometer', 'micrometer')
        )
        assert viewer.layers.selection.active is layer

        ureg = get_pint_ureg(viewer)
        assert ureg is not None
        assert str(ureg.micrometer) == 'micrometer'


class TestGetAxesUnits:
    def test_get_axes_units_no_active_layer(self):
        viewer = ViewerModel()
        units = get_axes_units(viewer)
        assert units == ()

    def test_get_axes_units_active_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(
            np.zeros((4, 3)), units=('micrometer', 'micrometer')
        )
        layer2 = viewer.add_image(np.zeros((2, 2)), units=('pixel', 'pixel'))

        assert viewer.layers.selection.active is layer2
        units = get_axes_units(viewer)
        assert units == ('pixel', 'pixel')

        viewer.layers.selection.active = layer1
        units = get_axes_units(viewer)
        assert units == ('micrometer', 'micrometer')


class TestSetAxesUnits:
    def test_set_axes_units_no_active_layer(self):
        viewer = ViewerModel()
        # should not raise error
        set_axes_units(viewer, ('micrometer', 'micrometer'))

    def test_set_axes_units_active_layer(self):
        viewer = ViewerModel()
        layer = viewer.add_image(np.zeros((4, 3)), units=('pixel', 'pixel'))

        assert viewer.layers.selection.active is layer

        set_axes_units(viewer, ('micrometer', 'micrometer'))
        assert layer.units == ('micrometer', 'micrometer')

    def test_set_axes_units_explicit_layer(self):
        """Test that explicit layer parameter is used, not active layer."""
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), units=('pixel', 'pixel'))
        layer2 = viewer.add_image(
            np.zeros((5, 6)), units=('micrometer', 'micrometer')
        )

        # layer2 is active but we modify layer1 explicitly
        assert viewer.layers.selection.active is layer2
        set_axes_units(viewer, ('nanometer', 'nanometer'), layer=layer1)

        assert layer1.units == ('nanometer', 'nanometer')
        assert layer2.units == ('micrometer', 'micrometer')  # unchanged


class TestGetAxesScales:
    def test_get_axes_scales_no_active_layer(self):
        viewer = ViewerModel()
        scales = get_axes_scales(viewer)
        assert scales == ()

    def test_get_axes_scales_active_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), scale=(1.0, 2.0))
        layer2 = viewer.add_image(np.zeros((2, 2)), scale=(0.5, 0.5))

        assert viewer.layers.selection.active is layer2
        scales = get_axes_scales(viewer)
        assert np.allclose(scales, (0.5, 0.5))

        viewer.layers.selection.active = layer1
        scales = get_axes_scales(viewer)
        assert np.allclose(scales, (1.0, 2.0))


class SetAxesScales:
    def test_set_axes_scales_no_active_layer(self):
        viewer = ViewerModel()
        # should not raise error
        set_axes_scales(viewer, (1.0, 1.0))

    def test_set_axes_scales_active_layer(self):
        viewer = ViewerModel()
        layer = viewer.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))

        assert viewer.layers.selection.active is layer

        set_axes_scales(viewer, (0.5, 0.5))
        assert np.allclose(layer.scale, (0.5, 0.5))

    def test_set_axes_scales_explicit_layer(self):
        """Test that explicit layer parameter is used, not active layer."""
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), scale=(1.0, 1.0))
        layer2 = viewer.add_image(np.zeros((5, 6)), scale=(2.0, 2.0))

        # layer2 is active but we modify layer1 explicitly
        assert viewer.layers.selection.active is layer2
        set_axes_scales(viewer, (0.1, 0.1), layer=layer1)

        assert np.allclose(layer1.scale, (0.1, 0.1))
        assert np.allclose(layer2.scale, (2.0, 2.0))  # unchanged


class TestGetAxesTranslations:
    def test_get_axes_translations_no_active_layer(self):
        viewer = ViewerModel()
        translations = get_axes_translations(viewer)
        assert translations == ()

    def test_get_axes_translations_active_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), translate=(0.0, 1.0))
        layer2 = viewer.add_image(np.zeros((2, 2)), translate=(2.0, 2.0))

        assert viewer.layers.selection.active is layer2
        translations = get_axes_translations(viewer)
        assert np.allclose(translations, (2.0, 2.0))

        viewer.layers.selection.active = layer1
        translations = get_axes_translations(viewer)
        assert np.allclose(translations, (0.0, 1.0))


class TestSetAxesTranslations:
    def test_set_axes_translations_no_active_layer(self):
        viewer = ViewerModel()
        # should not raise error
        set_axes_translations(viewer, (0.0, 0.0))

    def test_set_axes_translations_active_layer(self):
        viewer = ViewerModel()
        layer = viewer.add_image(np.zeros((4, 3)), translate=(0.0, 0.0))

        assert viewer.layers.selection.active is layer

        set_axes_translations(viewer, (1.0, 1.0))
        assert np.allclose(layer.translate, (1.0, 1.0))

    def test_set_axes_translations_explicit_layer(self):
        """Test that explicit layer parameter is used, not active layer."""
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3)), translate=(0.0, 0.0))
        layer2 = viewer.add_image(np.zeros((5, 6)), translate=(2.0, 2.0))

        # layer2 is active but we modify layer1 explicitly
        assert viewer.layers.selection.active is layer2
        set_axes_translations(viewer, (3.0, 3.0), layer=layer1)

        assert np.allclose(layer1.translate, (3.0, 3.0))
        assert np.allclose(layer2.translate, (2.0, 2.0))  # unchanged


class TestGetLayerDataShape:
    def test_get_layer_data_shape_none_layer(self):
        shape = get_layer_data_shape(None)
        assert shape == ()

    def test_get_layer_data_shape_with_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3, 2)))
        layer2 = viewer.add_image(np.zeros((2, 2)))

        shape1 = get_layer_data_shape(layer1)
        assert shape1 == (4, 3, 2)

        shape2 = get_layer_data_shape(layer2)
        assert shape2 == (2, 2)


class TestGetLayerDataDtype:
    def test_get_layer_data_dtype_none_layer(self):
        dtype = get_layer_data_dtype(None)
        assert dtype == ''

    def test_get_layer_data_dtype_with_layer(self):
        viewer = ViewerModel()
        layer1 = viewer.add_image(np.zeros((4, 3), dtype=np.float32))
        layer2 = viewer.add_image(np.zeros((2, 2), dtype=np.uint8))

        dtype1 = get_layer_data_dtype(layer1)
        assert dtype1 == 'float32'

        dtype2 = get_layer_data_dtype(layer2)
        assert dtype2 == 'uint8'


class TestGetLayerSourcePath:
    def test_get_layer_source_path_none_layer(self):
        path = get_layer_source_path(None)
        assert path == ''

    # TODO: source is immutable
    # def test_get_layer_source_path_with_layer(self):
    #     viewer = ViewerModel()
    #     layer = viewer.add_image(np.zeros((4, 3)))

    #     # By default, layers don't have a source path
    #     path = get_layer_source_path(layer)
    #     assert path == ''

    #     # Can manually set source path
    #     layer.source.path = 'path/to/image.tif'
    #     path = get_layer_source_path(layer)
    #     assert path == 'path/to/image.tif'


class TestGetLayerDimensions:
    def test_get_layer_dimensions_none_layer(self):
        dims = get_layer_dimensions(None)
        assert dims == 0

    def test_get_layer_dimensions_with_layer(self):
        viewer = ViewerModel()
        layer_2d = viewer.add_image(np.zeros((4, 3)))
        layer_3d = viewer.add_image(np.zeros((5, 4, 3)))

        dims_2d = get_layer_dimensions(layer_2d)
        assert dims_2d == 2

        dims_3d = get_layer_dimensions(layer_3d)
        assert dims_3d == 3
