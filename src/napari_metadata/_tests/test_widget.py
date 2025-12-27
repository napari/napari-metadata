from typing import TYPE_CHECKING, Tuple

import numpy as np
import pytest
from napari.components import ViewerModel
from napari.layers import (
    Image,
    Labels,
    Points,
    Shapes,
    Surface,
    Tracks,
    Vectors,
)

from napari_metadata import MetadataWidget
from napari_metadata._axes_widget import AxesWidget
from napari_metadata._axis_type import AxisType
from napari_metadata._model import (
    EXTRA_METADATA_KEY,
    ExtraMetadata,
    OriginalMetadata,
    SpaceAxis,
    SpaceUnits,
    TimeAxis,
    TimeUnits,
    extra_metadata,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture(
    scope='module',
    params=[
        (Image, {'data': np.zeros((4, 3))}),
        (Image, {'data': np.zeros((5, 4, 3), dtype=np.uint8), 'rgb': True}),
        (Labels, {'data': np.zeros((4, 3), dtype=int)}),
        (Points, {'data': np.zeros((1, 2))}),
        (Shapes, {'data': [np.zeros((4, 2))]}),
        (Vectors, {'data': np.zeros((1, 2, 2))}),
        (Tracks, {'data': np.zeros((1, 4))}),
        (
            Surface,
            {'data': (np.zeros((3, 3)), np.array([[0, 1, 2]], dtype=int))},
        ),
    ],
    ids=lambda param: param[0].__name__,
)
def layer(request):
    Type, kwargs = request.param
    return Type(**kwargs)


def test_init_with_no_layers(qtbot: 'QtBot'):
    viewer = ViewerModel()
    assert viewer.layers.selection == set()

    widget = make_metadata_widget(qtbot, viewer)

    assert widget.currentWidget() is widget._info_widget


def test_init_with_one_selected_layer(qtbot: 'QtBot', layer):
    viewer = ViewerModel()
    viewer.add_layer(layer)
    assert viewer.layers.selection == {layer}

    widget = make_metadata_widget(qtbot, viewer)

    assert widget.currentWidget() is widget._editable_widget
    assert axis_names(widget) == tuple(str(d) for d in range(layer.ndim))
    assert are_axis_widgets_visible(widget) == (True,) * layer.ndim


def test_init_with_one_unselected_2d_image_and_one_selected_3d_image(
    qtbot: 'QtBot',
):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3)))
    viewer.add_image(np.empty((4, 3, 2)))
    assert viewer.layers.selection == {viewer.layers[1]}

    widget = make_metadata_widget(qtbot, viewer)

    assert axis_names(widget) == ('0', '1', '2')
    assert are_axis_widgets_visible(widget) == (True, True, True)


def test_init_with_one_selected_2d_image_and_one_unselected_3d_image(
    qtbot: 'QtBot',
):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3, 2)))
    viewer.add_image(np.empty((4, 3)))
    assert viewer.layers.selection == {viewer.layers[1]}

    widget = make_metadata_widget(qtbot, viewer)

    assert axis_names(widget) == ('0', '1', '2')
    assert are_axis_widgets_visible(widget) == (False, True, True)


def test_selected_layer_from_2d_to_3d(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3, 2)))
    viewer.add_image(np.empty((4, 3)))
    assert viewer.layers.selection == {viewer.layers[1]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (False, True, True)

    viewer.layers.selection = {viewer.layers[0]}

    assert are_axis_widgets_visible(widget) == (True, True, True)


def test_selected_layer_from_3d_to_2d(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3)))
    viewer.add_image(np.empty((4, 3, 2)))
    assert viewer.layers.selection == {viewer.layers[1]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (True, True, True)

    viewer.layers.selection = {viewer.layers[0]}

    assert are_axis_widgets_visible(widget) == (False, True, True)


def test_add_2d_image_to_3d_image(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3, 2)))
    assert viewer.layers.selection == {viewer.layers[0]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (True, True, True)

    viewer.add_image(np.empty((4, 3)))

    assert viewer.layers.selection == {viewer.layers[1]}
    assert are_axis_widgets_visible(widget) == (False, True, True)


def test_add_3d_image_to_2d_image(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3)))
    assert viewer.layers.selection == {viewer.layers[0]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (True, True)

    viewer.add_image(np.empty((4, 3, 2)))

    assert viewer.layers.selection == {viewer.layers[1]}
    assert are_axis_widgets_visible(widget) == (True, True, True)


def test_remove_only_2d_image(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3)))
    assert viewer.layers.selection == {viewer.layers[0]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (True, True)

    viewer.layers.pop()

    assert viewer.layers.selection == set()
    assert axis_names(widget) == ('0', '1')
    assert are_axis_widgets_visible(widget) == (False, False)


def test_remove_only_3d_image(qtbot: 'QtBot'):
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3, 2)))
    assert viewer.layers.selection == {viewer.layers[0]}
    widget = make_metadata_widget(qtbot, viewer)
    assert are_axis_widgets_visible(widget) == (True, True, True)

    viewer.layers.pop()

    assert viewer.layers.selection == set()
    assert widget.currentWidget() is widget._info_widget


def test_set_axis_name(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    first_axis_widget = axes_widget(widget).axis_widgets()[0]
    layer = viewer.layers[0]
    new_name = 'y'
    assert first_axis_widget.name.text() != new_name
    assert extra_metadata(layer).axes[0].name != new_name
    assert viewer.dims.axis_labels[0] != new_name

    first_axis_widget.name.setText(new_name)

    assert viewer.dims.axis_labels[0] == new_name
    assert extra_metadata(layer).axes[0].name == new_name


def test_set_axis_type(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    first_axis_widget = axes_widget(widget).axis_widgets()[0]
    layer = viewer.layers[0]
    new_type = AxisType.CHANNEL
    assert first_axis_widget.name.text() != str(new_type)
    assert extra_metadata(layer).axes[0].get_type() != new_type

    first_axis_widget.type.setCurrentText(str(new_type))

    assert extra_metadata(layer).axes[0].get_type() == new_type


def test_set_viewer_axis_label(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    first_axis_widget = axes_widget(widget).axis_widgets()[0]
    layer = viewer.layers[0]
    new_name = 'y'
    assert viewer.dims.axis_labels[0] != new_name
    assert extra_metadata(layer).axes[0].name != new_name
    assert first_axis_widget.name.text() != new_name

    viewer.dims.axis_labels = [new_name, viewer.dims.axis_labels[1]]

    assert first_axis_widget.name.text() == new_name
    assert extra_metadata(layer).axes[0].name == new_name


def test_set_space_unit(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    space_units_widget = widget._editable_widget._spatial_units
    layer = viewer.layers[0]
    new_unit = 'millimeter'
    assert space_units_widget.currentText() != new_unit
    assert extra_metadata(layer).axes[0].get_unit_name() != new_unit
    assert viewer.scale_bar.unit != new_unit

    space_units_widget.setCurrentText(new_unit)

    assert viewer.scale_bar.unit == new_unit
    assert extra_metadata(layer).axes[0].get_unit_name() == new_unit


def test_set_viewer_scale_bar_unit(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    space_units_widget = widget._editable_widget._spatial_units
    new_unit = 'millimeter'
    assert viewer.scale_bar.unit != new_unit
    assert space_units_widget.currentText() != new_unit

    viewer.scale_bar.unit = new_unit

    assert space_units_widget.currentText() == new_unit


def test_set_viewer_scale_bar_unit_to_none(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    space_units_widget = widget._editable_widget._spatial_units
    viewer.scale_bar.unit = 'millimeter'
    assert space_units_widget.currentText() != 'none'

    viewer.scale_bar.unit = None

    assert space_units_widget.currentText() == 'none'


def test_set_viewer_scale_bar_unit_to_unknown(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    viewer.scale_bar.unit = 'millimeter'
    space_units_widget = widget._editable_widget._spatial_units
    assert space_units_widget.currentText() != 'none'

    # Supported by pint/napari, but not supported by our widget.
    viewer.scale_bar.unit = 'furlong'

    assert space_units_widget.currentText() == 'none'


def test_set_viewer_scale_bar_unit_to_abbreviation(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    space_units_widget = widget._editable_widget._spatial_units
    assert viewer.scale_bar.unit != 'mm'
    assert space_units_widget.currentText() != 'millimeter'

    viewer.scale_bar.unit = 'mm'

    assert space_units_widget.currentText() == 'millimeter'


def test_set_time_unit(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    time_units_widget = widget._editable_widget._temporal_units
    name_type_widget = axes_widget(widget).axis_widgets()[0]
    name_type_widget.type.setCurrentText('time')
    layer = viewer.layers[0]
    new_unit = 'millisecond'
    assert time_units_widget.currentText() != new_unit
    assert extra_metadata(layer).axes[0].get_unit_name() != new_unit

    time_units_widget.setCurrentText(new_unit)

    assert extra_metadata(layer).axes[0].get_unit_name() == new_unit


def test_set_layer_scale(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    layer = viewer.layers[0]
    pixel_width_widget = (
        widget._editable_widget._spacing_widget._axis_widgets()[0].spacing
    )
    assert layer.scale[0] == pixel_width_widget.value()
    assert pixel_width_widget.value() != 4.5

    layer.scale = (4.5, layer.scale[1])

    assert pixel_width_widget.value() == 4.5


def test_set_layer_translate(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    layer = viewer.layers[0]
    translate_widget = widget._editable_widget._spacing_widget._axis_widgets()[
        0
    ].translate
    assert layer.translate[0] == translate_widget.value()
    assert translate_widget.value() != -2

    layer.translate = (-2, layer.translate[1])

    assert translate_widget.value() == -2


def test_set_pixel_size(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    layer = viewer.layers[0]
    pixel_width_widget = (
        widget._editable_widget._spacing_widget._axis_widgets()[0].spacing
    )
    assert pixel_width_widget.value() == layer.scale[0]
    assert layer.scale[0] != 4.5

    pixel_width_widget.setValue(4.5)

    assert layer.scale[0] == 4.5


def test_set_translate(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    layer = viewer.layers[0]
    translate_widget = widget._editable_widget._spacing_widget._axis_widgets()[
        0
    ].translate
    assert translate_widget.value() == layer.translate[0]
    assert layer.translate[0] != -2

    translate_widget.setValue(-2)

    assert layer.translate[0] == -2


def test_restore_defaults(qtbot: 'QtBot'):
    viewer, widget = make_viewer_with_one_image_and_widget(qtbot)
    layer = viewer.layers[0]
    extras = extra_metadata(layer)
    extras.original = OriginalMetadata(
        axes=(
            TimeAxis(name='t', unit=TimeUnits.NANOSECOND),
            SpaceAxis(name='u', unit=SpaceUnits.CENTIMETER),
        ),
        name='kermit',
        scale=(2, 3),
        translate=(-1, 0.5),
    )
    assert layer.name != extras.original.name
    assert tuple(layer.scale) != extras.original.scale
    assert tuple(layer.translate) != extras.original.translate
    assert tuple(extras.axes) != extras.original.axes
    assert widget._editable_widget._spatial_units.currentText() != 'centimeter'
    assert (
        widget._editable_widget._temporal_units.currentText() != 'nanosecond'
    )

    widget._editable_widget._restore_defaults.setEnabled(True)
    widget._editable_widget._restore_defaults.click()

    assert layer.name == extras.original.name
    assert tuple(layer.scale) == extras.original.scale
    assert tuple(layer.translate) == extras.original.translate
    assert tuple(extras.axes) == extras.original.axes
    assert widget._editable_widget._spatial_units.currentText() == 'centimeter'
    assert (
        widget._editable_widget._temporal_units.currentText() == 'nanosecond'
    )


def test_add_image_with_existing_metadata(qtbot: 'QtBot'):
    viewer = ViewerModel()
    widget = make_metadata_widget(qtbot, viewer)
    image = Image(np.zeros((4, 5, 6)), rgb=False)
    axes = [
        TimeAxis(name='t', unit=TimeUnits.SECOND),
        SpaceAxis(name='y', unit=SpaceUnits.MILLIMETER),
        SpaceAxis(name='x', unit=SpaceUnits.MILLIMETER),
    ]

    image.metadata[EXTRA_METADATA_KEY] = ExtraMetadata(axes=axes)
    assert viewer.dims.axis_labels != ('t', 'y', 'x')
    assert viewer.scale_bar.unit is None
    assert widget._editable_widget._spatial_units.currentText() != 'millimeter'
    assert widget._editable_widget._temporal_units.currentText() != 'second'

    viewer.add_layer(image)

    axes_after = extra_metadata(image).axes
    assert axes_after[0].name == 't'
    assert axes_after[1].name == 'y'
    assert axes_after[2].name == 'x'
    assert viewer.dims.axis_labels == ('t', 'y', 'x')
    assert axis_names(widget) == ('t', 'y', 'x')

    assert axes_after[0].get_type() == AxisType.TIME
    assert axes_after[1].get_type() == AxisType.SPACE
    assert axes_after[2].get_type() == AxisType.SPACE
    widget_axis_types = tuple(
        AxisType.from_name(w.type.currentText())
        for w in axes_widget(widget).axis_widgets()
    )
    assert widget_axis_types == (AxisType.TIME, AxisType.SPACE, AxisType.SPACE)

    assert axes_after[0].get_unit_name() == 'second'
    assert axes_after[1].get_unit_name() == 'millimeter'
    assert axes_after[2].get_unit_name() == 'millimeter'
    assert viewer.scale_bar.unit == 'millimeter'
    assert widget._editable_widget._spatial_units.currentText() == 'millimeter'
    assert widget._editable_widget._temporal_units.currentText() == 'second'


def axes_widget(widget: MetadataWidget) -> AxesWidget:
    return widget._editable_widget._axes_widget


def axis_names(widget: MetadataWidget) -> Tuple[str, ...]:
    return axes_widget(widget).axis_names()


def are_axis_widgets_visible(widget: MetadataWidget) -> Tuple[bool, ...]:
    axes_widget = widget._editable_widget._axes_widget
    return tuple(
        map(
            lambda row: row.name.isVisibleTo(widget),
            axes_widget.axis_widgets(),
        )
    )


def make_metadata_widget(
    qtbot: 'QtBot', viewer: ViewerModel
) -> MetadataWidget:
    widget = MetadataWidget(viewer)
    qtbot.addWidget(widget)
    return widget


def make_viewer_with_one_image_and_widget(
    qtbot: 'QtBot',
) -> Tuple[ViewerModel, MetadataWidget]:
    viewer = ViewerModel()
    viewer.add_image(np.empty((4, 3)))
    assert viewer.layers.selection == {viewer.layers[0]}
    widget = make_metadata_widget(qtbot, viewer)
    return viewer, widget
