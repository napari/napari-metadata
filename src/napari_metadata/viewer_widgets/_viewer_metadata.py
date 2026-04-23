from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from napari_metadata.viewer_widgets._dims import DimsWidget
from napari_metadata.viewer_widgets._scale_bar import ScaleBarWidget
from napari_metadata.widgets._containers import (
    CollapsibleSectionContainer,
    Orientation,
)

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
        self._widget_parent: QWidget | None = self.parent()
        self._current_orientation: Orientation | None = None

        # Expanded states for each section
        self._dims_expanded: bool = False
        self._scale_bar_expanded: bool = False

        # ── Persistent component instances ──────────────────────────
        self._dims_instance = DimsWidget(napari_viewer, parent=self)

        self._scale_bar_instance = ScaleBarWidget(napari_viewer, parent=self)

        self._layout: QVBoxLayout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._content_widget: QWidget | None = None
        self._content_layout: QVBoxLayout | QHBoxLayout | None = None
        self._dims_section: CollapsibleSectionContainer | None = None
        self._scale_bar_section: CollapsibleSectionContainer | None = None

        self._rebuild_content(self._get_required_orientation())

    def showEvent(self, event) -> None:
        super().showEvent(event)

        parent_widget = self.parent()
        if parent_widget is None or not isinstance(parent_widget, QDockWidget):
            return

        self._widget_parent = parent_widget
        self._widget_parent.dockLocationChanged.connect(
            self._on_dock_location_changed
        )

    def _get_required_orientation(self) -> Orientation:
        """Determine vertical vs horizontal based on the dock widget area."""
        if not isinstance(self._widget_parent, QDockWidget):
            return 'vertical'
        dock = self._widget_parent
        main_window = dock.parent()
        if not isinstance(main_window, QMainWindow):
            return 'vertical'
        area = main_window.dockWidgetArea(dock)
        if (
            area == Qt.DockWidgetArea.LeftDockWidgetArea
            or area == Qt.DockWidgetArea.RightDockWidgetArea
            or dock.isFloating()
        ):
            return 'vertical'
        return 'horizontal'

    def _on_dock_location_changed(self) -> None:
        orientation = self._get_required_orientation()
        if orientation != self._current_orientation:
            self._rebuild_content(orientation)

    def _rebuild_content(self, orientation: Orientation) -> None:
        self._teardown_content()

        self._content_widget = QWidget(self)
        layout_class = (
            QVBoxLayout if orientation == 'vertical' else QHBoxLayout
        )
        self._content_layout = layout_class(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        self._dims_section = CollapsibleSectionContainer(
            self,
            'Viewer dims',
            orientation=orientation,
            on_toggle=self._on_dims_toggled,
        )
        self._dims_section.set_content_widget(self._dims_instance)
        self._dims_section.setExpanded(self._dims_expanded)

        self._scale_bar_section = CollapsibleSectionContainer(
            self,
            'Scale bar',
            orientation=orientation,
            on_toggle=self._on_scale_bar_toggled,
        )
        self._scale_bar_section.set_content_widget(self._scale_bar_instance)
        self._scale_bar_section.setExpanded(self._scale_bar_expanded)

        self._content_layout.addWidget(self._dims_section)
        self._content_layout.addWidget(self._scale_bar_section)
        self._content_layout.addStretch()
        self._layout.addWidget(self._content_widget)
        self._current_orientation = orientation

    def _teardown_content(self) -> None:
        if self._content_widget is None:
            return

        self._dims_instance.setParent(self)
        self._scale_bar_instance.setParent(self)

        self._layout.removeWidget(self._content_widget)
        self._content_widget.deleteLater()
        self._content_widget = None
        self._content_layout = None
        self._dims_section = None
        self._scale_bar_section = None

    def _on_dims_toggled(self, checked: bool) -> None:
        self._dims_expanded = checked

    def _on_scale_bar_toggled(self, checked: bool) -> None:
        self._scale_bar_expanded = checked
