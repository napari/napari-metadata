"""MetadataWidget — top-level dock widget for napari-metadata.

This module contains the main plugin widget contributed to napari via the
npe2 manifest.  It manages three collapsible sections (file metadata,
axes metadata, axes inheritance) and switches between vertical and
horizontal layouts depending on the dock widget area.

Orientation switching works by tearing down and rebuilding the content
page.  The component *instances* (``FileGeneralMetadata``,
``AxisMetadata``, ``InheritanceWidget``) persist across rebuilds — only
the container widgets and grid layouts are recreated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from napari.utils.notifications import show_info
from qtpy.QtCore import QObject, Qt
from qtpy.QtGui import QShowEvent
from qtpy.QtWidgets import (
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from napari_metadata.layer_utils import resolve_layer
from napari_metadata.widgets._axis import AxisMetadata
from napari_metadata.widgets._base import AxisComponentBase
from napari_metadata.widgets._containers import (
    CollapsibleSectionContainer,
    HorizontalOnlyOuterScrollArea,
    Orientation,
)
from napari_metadata.widgets._file import FileGeneralMetadata
from napari_metadata.widgets._inheritance import InheritanceWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer

_CONTENT_PAGE = 0
_NO_LAYER_PAGE = 1


class MetadataWidget(QWidget):
    """Top-level dock widget for viewing and editing layer metadata.

    Layout architecture:

    * A ``QStackedLayout`` holds two pages: a *content page* (index 0)
      and a *no-layer placeholder* (index 1).
    * The content page contains a single orientation-appropriate
      ``QScrollArea`` with three ``CollapsibleSectionContainer`` children.
    * On orientation or layer change the content page is torn down and
      rebuilt via ``_rebuild_content``.  Component **instances** persist;
      only the container widgets and grid layouts are recreated.
    """

    def __init__(self, napari_viewer: ViewerModel) -> None:
        super().__init__()
        self._viewer = napari_viewer
        self._napari_viewer = napari_viewer
        self._selected_layer: Layer | None = None
        self._current_orientation: Orientation | None = None
        self._widget_parent: QObject | None = self.parent()
        self._already_shown: bool = False
        self._rebuilding: bool = False

        # ── Persistent component instances ──────────────────────────
        self._general_metadata_instance = FileGeneralMetadata(
            napari_viewer, self
        )
        self._axis_metadata_instance = AxisMetadata(napari_viewer, self)
        self._inheritance_instance = InheritanceWidget(
            napari_viewer,
            on_apply_inheritance=self.apply_inheritance_to_current_layer,
            parent=self,
        )

        # ── Stacked layout (content + no-layer) ────────────────────
        self._stacked_layout = QStackedLayout()
        self._stacked_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._stacked_layout)

        # Content page wrapper — holds the orientation-specific scroll area
        self._content_page = QWidget(self)
        self._content_page_layout = QVBoxLayout(self._content_page)
        self._content_page_layout.setContentsMargins(0, 0, 0, 0)
        self._stacked_layout.addWidget(self._content_page)  # index 0

        # No-layer page
        no_layer_page = QWidget(self)
        no_layer_layout = QVBoxLayout(no_layer_page)
        no_layer_layout.setContentsMargins(0, 0, 0, 0)
        no_layer_label = QLabel('Select a layer to display its metadata')
        no_layer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_layer_label.setStyleSheet('font-weight: bold;')
        no_layer_layout.addWidget(no_layer_label)
        no_layer_layout.addStretch(1)
        self._stacked_layout.addWidget(no_layer_page)  # index 1

        # Track the current scroll area for teardown
        self._scroll_area: QScrollArea | None = None
        self._inheritance_section: CollapsibleSectionContainer | None = None

        # Start on the no-layer page — no layer is selected at construction
        self._stacked_layout.setCurrentIndex(_NO_LAYER_PAGE)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def showEvent(self, a0: QShowEvent | None) -> None:
        if self._already_shown:
            return

        super().showEvent(a0)

        parent_widget = self.parent()
        if parent_widget is None or not isinstance(parent_widget, QDockWidget):
            return

        self._widget_parent = parent_widget
        self._viewer.layers.selection.events.active.connect(
            self._on_selected_layers_changed
        )
        self._widget_parent.dockLocationChanged.connect(
            self._on_dock_location_changed
        )
        self._on_selected_layers_changed()
        self._already_shown = True

    def _on_dock_location_changed(self) -> None:
        """Handle dock widget location change — rebuild if orientation changed."""
        if self._selected_layer is None:
            return
        orientation = self._get_required_orientation()
        if orientation != self._current_orientation:
            self._rebuild_content(orientation)

    def _on_selected_layers_changed(self) -> None:
        """Handle layer selection change — always refresh page."""
        layer: Layer | None = self._viewer.layers.selection.active
        if layer is self._selected_layer:
            return

        if self._selected_layer is not None:
            self._selected_layer.events.name.disconnect(
                self._on_selected_layer_name_changed
            )

        if layer is not None:
            layer.events.name.connect(self._on_selected_layer_name_changed)

        self._selected_layer = layer
        self._refresh_page()

    def _on_selected_layer_name_changed(self) -> None:
        """Refresh file metadata when the active layer's name changes."""
        if self._selected_layer is None:
            return
        for component in self._general_metadata_instance.components:
            component.load_entries()

    # ------------------------------------------------------------------
    # Orientation detection
    # ------------------------------------------------------------------

    def _get_required_orientation(self) -> Orientation:
        """Determine vertical vs horizontal based on the dock widget area."""
        if not isinstance(self._widget_parent, QDockWidget):
            return 'vertical'
        dock = self._widget_parent
        main_window = cast(QMainWindow, dock.parent())
        area = main_window.dockWidgetArea(dock)
        if (
            area == Qt.DockWidgetArea.LeftDockWidgetArea
            or area == Qt.DockWidgetArea.RightDockWidgetArea
            or dock.isFloating()
        ):
            return 'vertical'
        return 'horizontal'

    # ------------------------------------------------------------------
    # Page management
    # ------------------------------------------------------------------

    def _refresh_page(self) -> None:
        """Show the correct page and rebuild content if a layer is active."""
        if self._selected_layer is None:
            self._stacked_layout.setCurrentIndex(_NO_LAYER_PAGE)
            self._current_orientation = None
            return

        orientation = self._get_required_orientation()
        self._rebuild_content(orientation)
        self._stacked_layout.setCurrentIndex(_CONTENT_PAGE)

    def _rebuild_content(self, orientation: Orientation) -> None:
        """Tear down and rebuild the content page for *orientation*."""
        if self._rebuilding:
            return
        self._rebuilding = True
        try:
            self._do_rebuild_content(orientation)
        finally:
            self._rebuilding = False

    def _do_rebuild_content(self, orientation: Orientation) -> None:
        is_vertical = orientation == 'vertical'

        # Detach persistent widgets so they survive container deletion
        self._detach_component_widgets()

        # Remove old scroll area
        if self._scroll_area is not None:
            self._content_page_layout.removeWidget(self._scroll_area)
            self._scroll_area.deleteLater()
            self._scroll_area = None

        # Create orientation-appropriate scroll area
        if is_vertical:
            scroll = QScrollArea(self._content_page)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
        else:
            scroll = HorizontalOnlyOuterScrollArea(self._content_page)
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        scroll.setWidgetResizable(True)
        self._scroll_area = scroll

        # Content inside the scroll area
        scroll_content = QWidget(scroll)
        layout_class = QVBoxLayout if is_vertical else QHBoxLayout
        sections_layout = layout_class(scroll_content)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(3)

        # Build three collapsible sections
        sections_layout.addWidget(self._build_file_section(orientation))
        sections_layout.addWidget(self._build_axis_section(orientation))

        self._inheritance_section = self._build_inheritance_section(
            orientation
        )
        sections_layout.addWidget(self._inheritance_section)
        sections_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        self._content_page_layout.addWidget(scroll)

        self._current_orientation = orientation
        self.setMinimumSize(50, 50)

    def _detach_component_widgets(self) -> None:
        """Reparent all persistent component widgets back to *self*.

        This ensures they are not destroyed when old containers are deleted
        via ``deleteLater()``.
        """
        for comp in self._general_metadata_instance.components:
            comp.component_label.setParent(self)
            comp.value_widget.setParent(self)

        for comp in self._axis_metadata_instance.components:
            comp.component_label.setParent(self)
            for i in range(comp.num_axes):
                for entry in comp.get_layout_entries(i):
                    for w in entry.widgets:
                        w.setParent(self)

        self._inheritance_instance.setParent(self)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_file_section(
        self, orientation: Orientation
    ) -> CollapsibleSectionContainer:
        """Build the file metadata collapsible section."""
        section = CollapsibleSectionContainer(
            self,
            'File metadata',
            orientation=orientation,
        )
        container = QWidget(self)
        grid = QGridLayout(container)
        self._populate_file_grid(grid, orientation)
        section.set_content_widget(container)
        return section

    def _build_axis_section(
        self, orientation: Orientation
    ) -> CollapsibleSectionContainer:
        """Build the axes metadata collapsible section."""
        section = CollapsibleSectionContainer(
            self,
            'Axes metadata',
            orientation=orientation,
        )
        container = QWidget(self)
        grid = QGridLayout(container)
        self._populate_axis_grid(grid, orientation)
        section.set_content_widget(container)
        return section

    def _build_inheritance_section(
        self, orientation: Orientation
    ) -> CollapsibleSectionContainer:
        """Build the axes inheritance collapsible section."""
        section = CollapsibleSectionContainer(
            self,
            'Axes inheritance',
            orientation=orientation,
            on_toggle=lambda checked: (
                self._axis_metadata_instance.set_checkboxes_visible(checked)
            ),
        )
        container = QWidget(self)
        layout = QGridLayout(container)
        layout.addWidget(self._inheritance_instance)
        section.set_content_widget(container)
        return section

    # ------------------------------------------------------------------
    # Grid population — file metadata
    # ------------------------------------------------------------------

    def _populate_file_grid(
        self, grid: QGridLayout, orientation: Orientation
    ) -> None:
        """Place file component widgets into *grid* for *orientation*."""
        is_vertical = orientation == 'vertical'
        row = 0

        for component in self._general_metadata_instance.components:
            component.load_entries()

            if is_vertical and component._under_label_in_vertical:
                grid.addWidget(component.component_label, row, 0, 1, 1)
                row += 1
                grid.addWidget(
                    component.value_widget,
                    row,
                    0,
                    1,
                    2,
                    Qt.AlignmentFlag.AlignTop,
                )
            else:
                grid.addWidget(component.component_label, row, 0, 1, 1)
                grid.addWidget(
                    component.value_widget,
                    row,
                    1,
                    1,
                    1,
                    Qt.AlignmentFlag.AlignLeft,
                )
            row += 1

        # Stretch settings
        if is_vertical:
            for r in range(grid.rowCount()):
                grid.setRowStretch(r, 0)
            grid.setRowStretch(grid.rowCount(), 1)
            for c in range(grid.columnCount()):
                grid.setColumnStretch(c, 0)
            grid.setColumnStretch(max(grid.columnCount() - 1, 0), 1)
        else:
            for r in range(grid.rowCount()):
                grid.setRowStretch(r, 1)
            for c in range(grid.columnCount()):
                grid.setColumnStretch(c, 0)
            grid.setColumnStretch(grid.columnCount(), 1)

    # ------------------------------------------------------------------
    # Grid population — axis metadata
    # ------------------------------------------------------------------

    def _populate_axis_grid(
        self, grid: QGridLayout, orientation: Orientation
    ) -> None:
        """Dispatch to orientation-specific axis grid builder."""
        components = self._axis_metadata_instance.components
        if orientation == 'vertical':
            _populate_axis_grid_vertical(grid, components)
        else:
            _populate_axis_grid_horizontal(grid, components)

    # ------------------------------------------------------------------
    # Inheritance
    # ------------------------------------------------------------------

    def apply_inheritance_to_current_layer(
        self, template_layer: Layer
    ) -> None:
        active_layer = resolve_layer(self._napari_viewer)
        if active_layer is None:
            return

        if active_layer.ndim != template_layer.ndim:
            show_info(
                'Inheritance layer must have same number of dimensions '
                'as current layer'
            )
            return

        for component in self._axis_metadata_instance.components:
            component.inherit_layer_properties(template_layer)

        # Rebuild to show inherited values
        self._refresh_page()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_dock_widget(self) -> QDockWidget | None:
        if isinstance(self._widget_parent, QDockWidget):
            return self._widget_parent
        return None


# ======================================================================
# Module-level helpers (no dependency on MetadataWidget state)
# ======================================================================


def _populate_axis_grid_vertical(
    grid: QGridLayout,
    components: list[AxisComponentBase],
) -> None:
    """Layout axis components stacked vertically (side dock position).

    Each component occupies a block of rows::

        Label:  | axis_name | value_widget(s) | checkbox |
                | axis_name | value_widget(s) | checkbox |
                ──────────── separator ────────────────────
        Label:  | ...
    """
    grid.setVerticalSpacing(8)
    row = 0
    max_cols = 0
    separator_rows: list[int] = []

    for idx, component in enumerate(components):
        col = 0
        grid.addWidget(component.component_label, row, col, 1, 1)
        col += 1
        component.load_entries()

        for axis_index in range(component.num_axes):
            setting_col = col
            max_row_span = 0
            col_span_sum = 0

            for entry in component.get_layout_entries(axis_index):
                for widget in entry.widgets:
                    widget.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Expanding,
                    )
                    grid.addWidget(
                        widget,
                        row,
                        setting_col,
                        entry.row_span,
                        entry.col_span,
                    )
                setting_col += entry.col_span
                col_span_sum += entry.col_span
                max_row_span = max(max_row_span, entry.row_span)

            max_cols = max(max_cols, col_span_sum)
            row += max_row_span

        if idx < len(components) - 1:
            separator_rows.append(row)
            row += 3

    # Separators
    total_cols = max_cols + 1
    for sep_row in separator_rows:
        _add_horizontal_separator(grid, sep_row, total_cols)

    # Stretch settings
    for r in range(grid.rowCount()):
        if r > row + 1:
            grid.setRowMinimumHeight(r, 0)
        grid.setRowStretch(r, 0)
    grid.setRowStretch(row + 1, 1)
    for c in range(grid.columnCount()):
        if c > max_cols:
            grid.setColumnMinimumWidth(c, 0)
        grid.setColumnStretch(c, 0)
    grid.setColumnStretch(max_cols, 1)
    grid.parentWidget().updateGeometry()


def _populate_axis_grid_horizontal(
    grid: QGridLayout,
    components: list[AxisComponentBase],
) -> None:
    """Layout axis components side by side (top/bottom dock position).

    Components are placed as column groups::

        | Label       | sep | Label       |
        | ax0 val cb  |     | ax0 val cb  |
        | ax1 val cb  |     | ax1 val cb  |
    """
    starting_col = 0
    max_rows = 0
    separator_cols: list[int] = []

    for idx, component in enumerate(components):
        current_col = starting_col
        current_row = 1  # row 0 reserved for the component label
        component.load_entries()

        max_axis_col_span = 0
        for axis_index in range(component.num_axes):
            setting_col = current_col
            max_row_span = 0
            col_sum = 0

            for entry in component.get_layout_entries(axis_index):
                for widget in entry.widgets:
                    widget.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Expanding,
                    )
                    grid.addWidget(
                        widget,
                        current_row,
                        setting_col,
                        entry.row_span,
                        entry.col_span,
                    )
                setting_col += entry.col_span
                col_sum += entry.col_span
                max_row_span = max(max_row_span, entry.row_span)

            max_axis_col_span = max(max_axis_col_span, col_sum)
            current_row += max_row_span

        max_rows = max(max_rows, current_row)

        component.component_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(component.component_label, 0, starting_col, 1, 1)

        if idx < len(components) - 1:
            separator_cols.append(starting_col + max_axis_col_span)

        starting_col += max_axis_col_span + 3

    # Separators
    total_rows = max_rows + 1
    for sep_col in separator_cols:
        _add_vertical_separator(grid, sep_col, total_rows)

    # Stretch settings
    for r in range(grid.rowCount()):
        if r > max_rows + 1:
            grid.setRowMinimumHeight(r, 0)
        grid.setRowStretch(r, 0)
    grid.setRowStretch(max_rows + 1, 1)
    for c in range(grid.columnCount()):
        if c > starting_col - 2:
            grid.setColumnMinimumWidth(c, 0)
        grid.setColumnStretch(c, 0)
    grid.setColumnStretch(starting_col - 2, 1)
    grid.parentWidget().updateGeometry()


def _add_horizontal_separator(
    grid: QGridLayout, row: int, col_span: int
) -> None:
    """Insert a horizontal separator (padding-line-padding) at *row*."""
    before = QWidget()
    before.setFixedHeight(2)
    before.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    grid.addWidget(before, row, 0, 1, col_span)

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet('color: #999; background-color: #999;')
    line.setFixedHeight(3)
    line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    grid.addWidget(line, row + 1, 0, 1, col_span)

    after = QWidget()
    after.setFixedHeight(2)
    after.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    grid.addWidget(after, row + 2, 0, 1, col_span)


def _add_vertical_separator(
    grid: QGridLayout, col: int, row_span: int
) -> None:
    """Insert a vertical separator (padding-line-padding) at *col*."""
    before = QWidget()
    before.setFixedWidth(2)
    before.setSizePolicy(
        QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
    )
    grid.addWidget(before, 0, col, row_span, 1)

    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet('color: #999; background-color: #999;')
    line.setFixedWidth(3)
    line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    grid.addWidget(line, 0, col + 1, row_span, 1)

    after = QWidget()
    after.setFixedWidth(2)
    after.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    grid.addWidget(after, 0, col + 2, row_span, 1)
