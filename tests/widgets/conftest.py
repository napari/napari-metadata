"""Shared fixtures for widget tests."""

import pytest
from napari.components import ViewerModel
from qtpy.QtWidgets import QWidget


@pytest.fixture
def viewer_model() -> ViewerModel:
    return ViewerModel()


@pytest.fixture
def parent_widget(qtbot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget
