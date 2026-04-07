from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from napari_metadata.viewer_widgets._dims_and_units import DimsAndUnitsWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel


class ViewerMetadataWidget(QWidget):
    """Top-level dock widget for viewing and editing viewer metadata."""

    def __init__(self, napari_viewer: ViewerModel) -> None:
        super().__init__()
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._napari_viewer = napari_viewer

        # Expanded states for each section
        self._dims_and_units_expanded: bool = False

        # ── Persistent component instances ──────────────────────────
        self._dims_and_units_instance = DimsAndUnitsWidget(self)

        self._layout: QVBoxLayout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._layout.addWidget(self._dims_and_units_instance)
