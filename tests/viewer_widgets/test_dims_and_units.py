from __future__ import annotations

import numpy as np
from napari.layers import Image

from napari_metadata.viewer_widgets._dims_and_units import (
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
