from __future__ import annotations

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
    # Don't show widgets in tests; headless assertions inspect state directly.
    return widget
