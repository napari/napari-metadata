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
    # don't use widget.show() in tests, because that causes each test to pop up a window
    # as such, using widget.isVisible() in tests will return False, but that's fine for our purposes
    # instead we CAN check for widget.isHidden() to verify that the widget is not visible in the headless state because
    # .isVisible() requires even the parent to be visible, while .isHidden() only checks the widget itself
    return widget
