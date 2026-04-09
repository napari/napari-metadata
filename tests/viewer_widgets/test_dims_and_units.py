from __future__ import annotations

import numpy as np
from napari.layers import Image
from qtpy.QtCore import Qt

from napari_metadata.viewer_widgets._dims_and_units import (
    AxisLabelsDisplayWidget,
    AxisLabelTableModel,
    LabelTable,
    solve_layer_to_viewer_labels,
    solve_setting_labels,
)


def _make_layer(**kwargs) -> Image:
    return Image(np.zeros((4, 3)), **kwargs)


class TestSolveLayerToViewerLabels:
    def test_returns_empty_labels_when_layer_is_none(self):
        assert solve_layer_to_viewer_labels(3, None) == ['', '', '']

    def test_left_pads_labels_when_layer_has_fewer_dims_than_viewer(self):
        layer = _make_layer(axis_labels=('y', 'x'))

        assert solve_layer_to_viewer_labels(4, layer) == ['', '', 'y', 'x']

    def test_keeps_labels_when_layer_ndim_matches_viewer(self):
        layer = _make_layer(axis_labels=('row', 'col'))

        assert solve_layer_to_viewer_labels(2, layer) == ['row', 'col']


class TestSolveSettingLabels:
    def test_uses_layer_labels_when_present(self):
        viewer_labels = ('time', 'plane', 'row', 'col')
        layer_labels = ['', '', 'y', 'x']

        assert solve_setting_labels(viewer_labels, layer_labels) == [
            '-4',
            '-3',
            'y',
            'x',
        ]

    def test_falls_back_to_default_index_labels_when_layer_labels_are_empty(
        self,
    ):
        viewer_labels = ('t', 'z', 'y', 'x')
        layer_labels = ['', '', '', '']

        assert solve_setting_labels(viewer_labels, layer_labels) == [
            '-4',
            '-3',
            '-2',
            '-1',
        ]

    def test_mixes_default_and_layer_labels(self):
        viewer_labels = ('t', 'z', 'y', 'x')
        layer_labels = ['', 'depth', '', 'column']

        assert solve_setting_labels(viewer_labels, layer_labels) == [
            '-4',
            'depth',
            '-2',
            'column',
        ]


class TestAxisLabelTableModel:
    def test_builds_rows_from_viewer_and_active_layer(self, viewer_model):
        viewer_model.dims.axis_labels = ('time', 'plane', 'row', 'col')
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
        )
        viewer_model.layers.selection.active = layer

        model = AxisLabelTableModel(viewer_model)

        assert model.rowCount() == 4
        assert model.columnCount() == 3
        assert [row.viewer_label for row in model.rows] == [
            'time',
            'plane',
            'row',
            'col',
        ]
        assert [row.layer_label for row in model.rows] == ['', '', 'y', 'x']
        assert [row.setting_label for row in model.rows] == [
            '-4',
            '-3',
            'y',
            'x',
        ]

    def test_header_data_exposes_horizontal_and_vertical_labels(
        self, viewer_model
    ):
        viewer_model.dims.axis_labels = ('z', 'y', 'x')
        model = AxisLabelTableModel(viewer_model)

        assert (
            model.headerData(
                0,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.DisplayRole,
            )
            == 'Viewer'
        )
        assert (
            model.headerData(
                2,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.DisplayRole,
            )
            == 'Setting'
        )
        assert (
            model.headerData(
                0,
                Qt.Orientation.Vertical,
                Qt.ItemDataRole.DisplayRole,
            )
            == '-3'
        )
        assert (
            model.headerData(
                2,
                Qt.Orientation.Vertical,
                Qt.ItemDataRole.DisplayRole,
            )
            == '-1'
        )

    def test_refresh_updates_rows_after_layer_axis_label_change(
        self, viewer_model
    ):
        viewer_model.dims.axis_labels = ('z', 'y', 'x')
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('row', 'col'),
        )
        viewer_model.layers.selection.active = layer
        model = AxisLabelTableModel(viewer_model)

        layer.axis_labels = ('new_row', 'new_col')
        model.refresh()

        assert [row.layer_label for row in model.rows] == [
            '',
            'new_row',
            'new_col',
        ]


class TestLabelTable:
    def test_builds_read_only_table_view(self, viewer_model, parent_widget):
        model = AxisLabelTableModel(viewer_model)
        table = LabelTable(model, parent_widget)

        assert table.model() is model
        assert not table.isSortingEnabled()
        assert not table.cornerButtonEnabled()
        assert table.selectionMode() == LabelTable.SelectionMode.NoSelection
        assert table.editTriggers() == LabelTable.EditTrigger.NoEditTriggers


class TestAxisLabelsDisplayWidget:
    def test_active_layer_change_refreshes_model(self, viewer_model, qtbot):
        viewer_model.dims.axis_labels = ('z', 'y', 'x')
        layer_a = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('row', 'col'),
        )
        layer_b = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('r', 'c'),
        )
        viewer_model.layers.selection.active = layer_a

        widget = AxisLabelsDisplayWidget(viewer_model)
        qtbot.addWidget(widget)

        assert [row.layer_label for row in widget._table_model.rows] == [
            '',
            'row',
            'col',
        ]

        viewer_model.layers.selection.active = layer_b

        assert [row.layer_label for row in widget._table_model.rows] == [
            '',
            'r',
            'c',
        ]

    def test_layer_axis_labels_event_refreshes_model(
        self, viewer_model, qtbot
    ):
        viewer_model.dims.axis_labels = ('z', 'y', 'x')
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('row', 'col'),
        )
        viewer_model.layers.selection.active = layer

        widget = AxisLabelsDisplayWidget(viewer_model)
        qtbot.addWidget(widget)

        layer.axis_labels = ('new_row', 'new_col')

        assert [row.layer_label for row in widget._table_model.rows] == [
            '',
            'new_row',
            'new_col',
        ]

    def test_viewer_axis_labels_event_refreshes_model(
        self, viewer_model, qtbot
    ):
        viewer_model.dims.axis_labels = ('z', 'y', 'x')
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('row', 'col'),
        )
        viewer_model.layers.selection.active = layer

        widget = AxisLabelsDisplayWidget(viewer_model)
        qtbot.addWidget(widget)

        viewer_model.dims.axis_labels = ('depth', 'height', 'width')

        assert [row.viewer_label for row in widget._table_model.rows] == [
            'depth',
            'height',
            'width',
        ]

    def test_apply_button_writes_setting_labels_to_viewer(
        self, viewer_model, qtbot
    ):
        viewer_model.dims.axis_labels = ('time', 'plane', 'row', 'col')
        layer = viewer_model.add_image(
            np.zeros((4, 3)),
            axis_labels=('y', 'x'),
        )
        viewer_model.layers.selection.active = layer

        widget = AxisLabelsDisplayWidget(viewer_model)
        qtbot.addWidget(widget)

        widget._apply_layer_labels_to_viewer()

        assert viewer_model.dims.axis_labels == ('-4', '-3', 'y', 'x')
