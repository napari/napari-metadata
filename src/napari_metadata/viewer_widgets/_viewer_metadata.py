from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from napari_metadata.viewer_widgets._dims_and_units import DimsAndUnitsWidget
from napari_metadata.viewer_widgets._scale_bar import ScaleBarWidget
from napari_metadata.widgets._containers import CollapsibleSectionContainer

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
        self._scale_bar_expanded: bool = False

        # ── Persistent component instances ──────────────────────────
        self._dims_and_units_instance = DimsAndUnitsWidget(
            napari_viewer, parent=self
        )

        self._scale_bar_instance = ScaleBarWidget(napari_viewer, parent=self)

        self._layout: QVBoxLayout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._dims_and_units_section = CollapsibleSectionContainer(
            self,
            'Viewer dims',
            on_toggle=self._on_dims_and_units_toggled,
        )
        self._dims_and_units_section.set_content_widget(
            self._dims_and_units_instance
        )
        self._dims_and_units_section.setExpanded(self._dims_and_units_expanded)

        self._scale_bar_section = CollapsibleSectionContainer(
            self,
            'Scale bar',
            on_toggle=self._on_scale_bar_toggled,
        )
        self._scale_bar_section.set_content_widget(self._scale_bar_instance)
        self._scale_bar_section.setExpanded(self._scale_bar_expanded)

        self._layout.addWidget(self._dims_and_units_section)
        self._layout.addWidget(self._scale_bar_section)
        self._layout.addStretch()

    def _on_dims_and_units_toggled(self, checked: bool) -> None:
        self._dims_and_units_expanded = checked

    def _on_scale_bar_toggled(self, checked: bool) -> None:
        self._scale_bar_expanded = checked
