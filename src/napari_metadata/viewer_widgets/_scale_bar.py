from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel


class ScaleBarWidget(QWidget):
    """Scale bar section of the viewer metadata widget."""

    def __init__(
        self,
        napari_viewer: ViewerModel,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self._napari_viewer = napari_viewer

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.addStretch()
