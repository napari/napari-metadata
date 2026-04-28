from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from napari_metadata.viewer_widgets._dims import DimsWidget
from napari_metadata.viewer_widgets._scale_bar import ScaleBarWidget
from napari_metadata.widgets._containers import (
    CollapsibleSectionContainer,
    HorizontalOnlyOuterScrollArea,
    Orientation,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel

_SECTIONS_SPACING = 3


def _allocate_section_extents(
    *,
    expanded: list[bool],
    collapsed_extents: list[int],
    preferred_extents: list[int],
    available: int,
    spacing: int,
) -> list[int]:
    """Distribute available pixels across collapsed and expanded sections."""
    extents = collapsed_extents.copy()
    expanded_indices = [
        index for index, is_expanded in enumerate(expanded) if is_expanded
    ]
    if not expanded_indices:
        return extents

    collapsed_total = sum(
        extent
        for extent, is_expanded in zip(
            collapsed_extents, expanded, strict=True
        )
        if not is_expanded
    )
    usable = max(available - spacing - collapsed_total, 0)

    preferred_by_index = {
        index: max(preferred_extents[index], collapsed_extents[index])
        for index in expanded_indices
    }
    minimum_total = sum(collapsed_extents[index] for index in expanded_indices)
    if usable <= minimum_total:
        return extents

    preferred_total = sum(
        preferred_by_index[index] for index in expanded_indices
    )
    if usable >= preferred_total:
        for index in expanded_indices:
            extents[index] = preferred_by_index[index]
        return extents

    remaining = usable
    for offset, index in enumerate(
        sorted(expanded_indices, key=lambda item: preferred_by_index[item])
    ):
        share = remaining // (len(expanded_indices) - offset)
        extent = max(
            collapsed_extents[index],
            min(preferred_by_index[index], share),
        )
        extents[index] = extent
        remaining -= extent

    return extents


class ViewerMetadataWidget(QWidget):
    """Top-level dock widget for viewing and editing viewer metadata."""

    def __init__(self, napari_viewer: ViewerModel) -> None:
        super().__init__()
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._napari_viewer = napari_viewer
        self._widget_parent: QWidget | None = self.parent()
        self._already_shown: bool = False
        self._current_orientation: Orientation | None = None
        self._scroll_area: QScrollArea | None = None

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
        if self._already_shown:
            return

        super().showEvent(event)

        parent_widget = self.parent()
        if parent_widget is None or not isinstance(parent_widget, QDockWidget):
            return

        self._widget_parent = parent_widget
        self._widget_parent.dockLocationChanged.connect(
            self._on_dock_location_changed
        )
        self._rebuild_content(self._get_required_orientation())
        self._already_shown = True

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_section_sizes()

    def eventFilter(self, watched, event) -> bool:
        viewport = (
            self._scroll_area.viewport()
            if self._scroll_area is not None
            else None
        )
        if (
            watched is viewport
            and event is not None
            and event.type()
            in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.LayoutRequest,
            )
        ):
            self._update_section_sizes()
        return super().eventFilter(watched, event)

    def sizeHint(self):
        if self._content_widget is not None:
            return self._content_widget.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        if self._content_widget is not None:
            return self._content_widget.minimumSizeHint()
        return super().minimumSizeHint()

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

        if orientation == 'vertical':
            scroll = QScrollArea(self)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll.setWidgetResizable(True)
        else:
            scroll = HorizontalOnlyOuterScrollArea(self)
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setWidgetResizable(True)
        self._scroll_area = scroll
        viewport = scroll.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)

        self._content_widget = QWidget(scroll)
        layout_class = (
            QVBoxLayout if orientation == 'vertical' else QHBoxLayout
        )
        self._content_layout = layout_class(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(_SECTIONS_SPACING)

        self._dims_section = CollapsibleSectionContainer(
            self,
            'Viewer dims',
            orientation=orientation,
            on_toggle=self._on_section_toggled,
        )
        self._dims_section.set_content_widget(self._dims_instance)
        self._dims_section.setExpanded(self._dims_expanded)

        self._scale_bar_section = CollapsibleSectionContainer(
            self,
            'Scale bar',
            orientation=orientation,
            on_toggle=self._on_section_toggled,
        )
        self._scale_bar_section.set_content_widget(self._scale_bar_instance)
        self._scale_bar_section.setExpanded(self._scale_bar_expanded)

        self._content_layout.addWidget(self._dims_section)
        self._content_layout.addWidget(self._scale_bar_section)
        self._content_layout.addStretch()
        scroll.setWidget(self._content_widget)
        self._layout.addWidget(scroll)
        self._current_orientation = orientation
        self._update_section_sizes()

    def _update_section_sizes(self) -> None:
        if self._current_orientation is None:
            return
        self._update_section_extents(self._current_orientation)

    def _update_section_extents(self, orientation: Orientation) -> None:
        if (
            self._current_orientation != orientation
            or self._scroll_area is None
        ):
            return

        sections = self._get_sections()
        if sections is None:
            return

        viewport = self._scroll_area.viewport()
        if viewport is None:
            return

        if orientation == 'horizontal':
            available = viewport.width()
            collapsed_extents = [
                section.collapsed_width_hint() for section in sections
            ]
            preferred_extents = [
                section.sizeHint().width() for section in sections
            ]
        else:
            available = viewport.height()
            collapsed_extents = [
                section.collapsed_height_hint() for section in sections
            ]
            preferred_extents = [
                section.sizeHint().height() for section in sections
            ]

        if available <= 0:
            return

        extents = _allocate_section_extents(
            expanded=[section.isExpanded() for section in sections],
            collapsed_extents=collapsed_extents,
            preferred_extents=preferred_extents,
            available=available,
            spacing=_SECTIONS_SPACING * max(len(sections) - 1, 0),
        )
        for section, extent in zip(sections, extents, strict=True):
            if orientation == 'horizontal':
                section.set_horizontal_section_width(extent)
            else:
                section.set_vertical_section_height(extent)

    def _get_sections(
        self,
    ) -> (
        tuple[CollapsibleSectionContainer, CollapsibleSectionContainer] | None
    ):
        if self._dims_section is None or self._scale_bar_section is None:
            return None
        return (self._dims_section, self._scale_bar_section)

    def _teardown_content(self) -> None:
        if self._dims_section is not None:
            self._dims_expanded = self._dims_section.isExpanded()
        if self._scale_bar_section is not None:
            self._scale_bar_expanded = self._scale_bar_section.isExpanded()

        self._dims_instance.setParent(self)
        self._scale_bar_instance.setParent(self)
        self._remove_scroll_area()

        self._content_widget = None
        self._content_layout = None
        self._dims_section = None
        self._scale_bar_section = None

    def _remove_scroll_area(self) -> None:
        if self._scroll_area is None:
            return

        viewport = self._scroll_area.viewport()
        if viewport is not None:
            viewport.removeEventFilter(self)
        self._layout.removeWidget(self._scroll_area)
        self._scroll_area.deleteLater()
        self._scroll_area = None

    def _on_section_toggled(self, _checked: bool) -> None:
        self._update_section_sizes()
