from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

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
        # self._dims_and_units_instance = DimsAndUnitsWidget(self)

        self._layout: QHBoxLayout = QHBoxLayout()
