"""Shared tests for the napari 0.9.0 dock size-policy shim.

napari 0.9.0 (napari/napari#9393) clamps every docked widget to
``(Preferred, Maximum)``, and both top-level dock widgets undo that clamp from
their ``showEvent`` (see ``napari_metadata.widgets._dock_size_policy``).  The
behaviour is identical for both widgets, so it is tested once here,
parametrized over the two classes, rather than duplicated in each widget's
test module.
"""

from __future__ import annotations

import pytest
from napari.components import ViewerModel
from qtpy.QtGui import QShowEvent
from qtpy.QtWidgets import QApplication, QSizePolicy

from napari_metadata.viewer_widgets import ViewerMetadataWidget
from napari_metadata.widgets import MetadataWidget

#: Top-level dock widgets that restore their ``Expanding`` policy on show.
_DOCK_WIDGET_CLASSES = (MetadataWidget, ViewerMetadataWidget)


@pytest.fixture(params=_DOCK_WIDGET_CLASSES)
def dock_widget(request, qtbot):
    """A real top-level dock widget on an empty ViewerModel (never shown)."""
    widget = request.param(ViewerModel())
    qtbot.addWidget(widget)
    return widget


def _show(widget) -> None:
    """Deliver a QShowEvent without actually showing a window."""
    QApplication.sendEvent(widget, QShowEvent())


class TestRestoreDockSizePolicyOnShow:
    """Regression: undo napari 0.9.0's clamp, without fighting the 0.9.1 fix."""

    def test_show_restores_expanding_after_napari_090_clamp(self, dock_widget):
        widget = dock_widget
        # The widget declares its own Expanding policy at construction...
        assert (
            widget.sizePolicy().verticalPolicy()
            == QSizePolicy.Policy.Expanding
        )

        # ...which napari 0.9.0 (napari/napari#9393) overrides with Maximum
        # when the widget is added to a dock.
        widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        assert widget.sizePolicy().verticalPolicy() == (
            QSizePolicy.Policy.Maximum
        )

        # Showing the widget re-asserts the intended policy.
        _show(widget)

        policy = widget.sizePolicy()
        assert policy.horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert policy.verticalPolicy() == QSizePolicy.Policy.Expanding

    def test_show_is_noop_when_napari_leaves_growable_widget_alone(
        self, dock_widget
    ):
        """The shim must not fight the upstream fix (napari/napari#9462).

        There, a widget that asks for vertical space keeps its vertical policy
        (only horizontal is normalized to Preferred); since the widget is no
        longer clamped to ``Maximum``, showing it must not change anything.
        """
        widget = dock_widget
        # Simulate the napari >= 0.9.1 outcome for this (growable) widget.
        widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )

        _show(widget)

        policy = widget.sizePolicy()
        assert policy.horizontalPolicy() == QSizePolicy.Policy.Preferred
        assert policy.verticalPolicy() == QSizePolicy.Policy.Expanding
