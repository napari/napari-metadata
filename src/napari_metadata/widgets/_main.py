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
    QLayout,
    QLayoutItem,
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
)
from napari_metadata.widgets._file import (
    FileGeneralMetadata,
    MetadataComponent,
)
from napari_metadata.widgets._inheritance import InheritanceWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


class MetadataWidget(QWidget):
    _selected_layer: Layer | None
    _inheritance_layer: Layer | None
    _stored_inheritances: dict[str, list[bool]] | None
    _stacked_layout: QStackedLayout
    _vertical_layout: QVBoxLayout | None
    _horizontal_layout: QHBoxLayout | None
    _no_layer_label: QLabel
    _widget_parent: QObject | None
    _current_orientation: str
    _active_listeners: bool
    _already_shown: bool

    _general_metadata_instance: FileGeneralMetadata
    _axis_metadata_instance: AxisMetadata

    def __init__(self, napari_viewer: ViewerModel):
        super().__init__()
        self._viewer = napari_viewer
        self._napari_viewer = napari_viewer
        self._selected_layer = None
        self._inheritance_layer = None
        self._stored_inheritances = None
        self._current_orientation = 'none'
        self._widget_parent = self.parent()
        self._active_listeners = True
        self._already_shown = False

        self._vertical_layout = QVBoxLayout()
        self._vertical_layout.setContentsMargins(0, 0, 0, 0)
        self._vertical_layout.setSpacing(3)

        self._horizontal_layout = QHBoxLayout()
        self._horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self._horizontal_layout.setSpacing(3)

        self._no_layer_layout = QVBoxLayout()
        self._no_layer_layout.setContentsMargins(0, 0, 0, 0)
        self._no_layer_layout.setSpacing(3)

        self._stacked_layout = QStackedLayout()
        self._stacked_layout.setContentsMargins(0, 0, 0, 0)
        self._stacked_layout.setSpacing(3)

        self._general_metadata_instance = FileGeneralMetadata(
            napari_viewer, self
        )

        self._vert_file_general_metadata_container: QWidget = QWidget(self)
        self._vert_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._vert_file_general_metadata_container.setLayout(
            self._vert_file_general_metadata_layout
        )
        self._hori_file_general_metadata_container: QWidget = QWidget(self)
        self._hori_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._hori_file_general_metadata_container.setLayout(
            self._hori_file_general_metadata_layout
        )

        self._axis_metadata_instance = AxisMetadata(napari_viewer, self)

        self._vert_axis_metadata_container: QWidget = QWidget(self)
        self._vert_axis_metadata_layout: QGridLayout = QGridLayout()
        self._vert_axis_metadata_container.setLayout(
            self._vert_axis_metadata_layout
        )
        self._hori_axis_metadata_container: QWidget = QWidget(self)
        self._hori_axis_metadata_layout: QGridLayout = QGridLayout()
        self._hori_axis_metadata_container.setLayout(
            self._hori_axis_metadata_layout
        )

        self._inheritance_instance: InheritanceWidget = InheritanceWidget(
            napari_viewer,
            on_apply_inheritance=self.apply_inheritance_to_current_layer,
            parent=self,
        )

        self._vert_inheritance_container: QWidget = QWidget(self)
        self._vert_inheritance_layout: QGridLayout = QGridLayout()
        self._vert_inheritance_container.setLayout(
            self._vert_inheritance_layout
        )
        self._hori_inheritance_container: QWidget = QWidget(self)
        self._hori_inheritance_layout: QGridLayout = QGridLayout()
        self._hori_inheritance_container.setLayout(
            self._hori_inheritance_layout
        )

        vertical_container: QScrollArea = QScrollArea(self)
        vertical_container.setWidgetResizable(True)
        vertical_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        vertical_container.container_orientation = 'vertical'

        vertical_content = QWidget(vertical_container)
        vertical_content.setLayout(self._vertical_layout)
        vertical_container.setWidget(vertical_content)

        self._stacked_layout.addWidget(vertical_container)

        self._collapsible_vertical_file_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'vertical_file_metadata',
            self,
            orientation='vertical',
        )
        self._collapsible_vertical_file_metadata._set_button_text(
            'File metadata'
        )
        self._collapsible_vertical_file_metadata._set_expanding_area_widget(
            self._vert_file_general_metadata_container
        )

        self._collapsible_vertical_editable_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'vertical_axes_metadata',
            self,
            orientation='vertical',
        )
        self._collapsible_vertical_editable_metadata._set_button_text(
            'Axes metadata'
        )
        self._collapsible_vertical_editable_metadata._set_expanding_area_widget(
            self._vert_axis_metadata_container
        )

        self._collapsible_vertical_inheritance: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'vertical_inheritance',
            self,
            orientation='vertical',
            on_toggle=lambda checked: self._resolve_show_inheritance_checkboxes(
                'vertical', checked
            ),
        )
        self._collapsible_vertical_inheritance._set_button_text(
            'Axes inheritance'
        )
        self._collapsible_vertical_inheritance._set_expanding_area_widget(
            self._vert_inheritance_container
        )

        self._vertical_layout.addWidget(
            self._collapsible_vertical_file_metadata
        )
        self._vertical_layout.addWidget(
            self._collapsible_vertical_editable_metadata
        )
        self._vertical_layout.addWidget(self._collapsible_vertical_inheritance)

        self._vertical_layout.addStretch(1)

        horizontal_container: HorizontalOnlyOuterScrollArea = (
            HorizontalOnlyOuterScrollArea(self)
        )
        horizontal_container.setWidgetResizable(True)
        horizontal_container.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        horizontal_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        horizontal_container.container_orientation = 'horizontal'

        horizontal_content: QWidget = QWidget(horizontal_container)
        horizontal_content.setLayout(self._horizontal_layout)
        horizontal_container.setWidget(horizontal_content)
        self._stacked_layout.addWidget(horizontal_container)

        self._collapsible_horizontal_file_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'horizontal_file_metadata',
            self,
            orientation='horizontal',
        )
        self._collapsible_horizontal_file_metadata._set_button_text(
            'File metadata'
        )
        self._collapsible_horizontal_file_metadata._set_expanding_area_widget(
            self._hori_file_general_metadata_container
        )

        self._collapsible_horizontal_editable_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'horizontal_axes_metadata',
            self,
            orientation='horizontal',
        )
        self._collapsible_horizontal_editable_metadata._set_button_text(
            'Axes metadata'
        )
        self._collapsible_horizontal_editable_metadata._set_expanding_area_widget(
            self._hori_axis_metadata_container
        )

        self._collapsible_horizontal_inheritance: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'horizontal_inheritance',
            self,
            orientation='horizontal',
            on_toggle=lambda checked: self._resolve_show_inheritance_checkboxes(
                'horizontal', checked
            ),
        )
        self._collapsible_horizontal_inheritance._set_button_text(
            'Axes inheritance'
        )
        self._collapsible_horizontal_inheritance._set_expanding_area_widget(
            self._hori_inheritance_container
        )

        self._horizontal_layout.addWidget(
            self._collapsible_horizontal_file_metadata
        )
        self._horizontal_layout.addWidget(
            self._collapsible_horizontal_editable_metadata
        )
        self._horizontal_layout.addWidget(
            self._collapsible_horizontal_inheritance
        )
        self._horizontal_layout.addStretch(1)

        no_layer_container: QWidget = QWidget(self)
        no_layer_container.container_orientation = 'no_layer'
        no_layer_container.setLayout(self._no_layer_layout)
        self._no_layer_label: QLabel = QLabel(
            'Select a layer to display its metadata'
        )
        self._no_layer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        self._no_layer_label.setStyleSheet('font-weight: bold;')  # type: ignore
        self._no_layer_layout.addWidget(self._no_layer_label)  # type: ignore
        self._no_layer_layout.addStretch(1)
        self._stacked_layout.addWidget(no_layer_container)

        self.setLayout(self._stacked_layout)

    def _on_selected_layer_name_changed(self) -> None:
        if self._selected_layer is None:
            return
        general_metadata_instance: FileGeneralMetadata = (
            self._general_metadata_instance
        )
        components_dict = (
            general_metadata_instance._file_metadata_components_dict
        )  # type: ignore
        general_metadata_component: MetadataComponent
        for general_metadata_component in components_dict.values():
            general_metadata_component.load_entries()

    def _disconnect_layer_params(self, layer: Layer) -> None:
        layer.events.name.disconnect(self._on_selected_layer_name_changed)

    def _connect_layer_params(self, layer: Layer) -> None:
        layer.events.name.connect(self._on_selected_layer_name_changed)

    def _on_selected_layers_changed(self) -> None:
        layer: Layer | None = None
        layer = self._viewer.layers.selection.active
        if layer == self._selected_layer:
            return
        if self._selected_layer is not None:
            self._disconnect_layer_params(self._selected_layer)
        if layer is None:
            self._selected_layer = None
        else:
            self._connect_layer_params(layer)
            self._selected_layer = layer

        self._update_orientation()

        current_orientation: str = self._current_orientation
        inheritance_expanded: bool
        if current_orientation == 'horizontal':
            inheritance_expanded = (
                self._collapsible_horizontal_inheritance.isExpanded()
            )
        else:
            inheritance_expanded = (
                self._collapsible_vertical_inheritance.isExpanded()
            )
        self._resolve_show_inheritance_checkboxes(
            current_orientation, inheritance_expanded
        )

    def showEvent(self, a0: QShowEvent | None) -> None:
        if self._already_shown:
            return

        super().showEvent(a0)

        parent_widget = self.parent()
        if parent_widget is None:
            return
        if isinstance(parent_widget, QDockWidget):
            napari_viewer = self._viewer
            if napari_viewer is None:
                return
            self._on_selected_layers_changed()
            self._widget_parent = parent_widget
            self._update_orientation()

            napari_viewer.layers.selection.events.active.connect(
                self._on_selected_layers_changed
            )
            self._widget_parent.dockLocationChanged.connect(
                self._on_dock_location_changed
            )

            self._already_shown = True

    def get_dock_widget(self) -> QDockWidget | None:
        if self._widget_parent is None:
            return None
        if isinstance(self._widget_parent, QDockWidget):
            return self._widget_parent
        else:
            return None

    def _on_dock_location_changed(self) -> None:
        self._update_orientation()

    def _get_required_orientation(self) -> str:
        dock_widget: QDockWidget = self.get_dock_widget()
        if dock_widget is None or not isinstance(dock_widget, QDockWidget):
            return 'vertical'
        else:
            main_window: QMainWindow = cast(QMainWindow, dock_widget.parent())
            dock_area: Qt.DockWidgetArea = main_window.dockWidgetArea(
                dock_widget
            )
            if (
                dock_area == Qt.DockWidgetArea.LeftDockWidgetArea
                or dock_area == Qt.DockWidgetArea.RightDockWidgetArea
                or dock_widget.isFloating()
            ):
                return 'vertical'
        return 'horizontal'

    def _update_orientation(self) -> None:
        if not self._active_listeners:
            return
        self._active_listeners = False
        required_orientation: str = self._get_required_orientation()
        selected_layer: Layer | None = self._selected_layer
        if selected_layer is None:
            required_orientation = 'no_layer'
        if required_orientation == self._current_orientation:
            self._active_listeners = True
            return
        elif required_orientation == 'vertical':
            self._set_layout_type('vertical')
        elif required_orientation == 'horizontal':
            self._set_layout_type('horizontal')
        else:
            self._set_layout_type('no_layer')
        self._active_listeners = True

        self.setMinimumSize(50, 50)

    def _reset_layout(self, layout: QLayout | None) -> None:
        if layout is None:
            return
        while layout.count():
            item: QLayoutItem | None = layout.takeAt(0)
            if item is not None:
                item_widget: QWidget | None = item.widget()
                if item_widget is None:
                    removing_second_layout: QLayout | None = item.layout()
                    if removing_second_layout is not None:
                        self._reset_layout(removing_second_layout)
                else:
                    item_widget.setParent(None)

    def _set_general_metadata_orientation(self, orientation: str) -> None:
        starting_row: int = 0
        starting_column: int = 0
        current_row: int = starting_row

        vert_file_layout: QGridLayout = self._vert_file_general_metadata_layout
        hori_file_layout: QGridLayout = self._hori_file_general_metadata_layout

        file_general_meta_instance: FileGeneralMetadata = (
            self._general_metadata_instance
        )
        components_dict = (
            file_general_meta_instance._file_metadata_components_dict
        )  # type: ignore

        if orientation == 'vertical':
            self._reset_layout(hori_file_layout)

            for name in components_dict:
                current_column: int = starting_column

                total_row_spans: int = 0

                general_component: MetadataComponent = components_dict[name]

                general_component_qlabel: QLabel = (
                    general_component._component_qlabel
                )
                vert_file_layout.addWidget(
                    general_component_qlabel, current_row, current_column, 1, 1
                )

                general_component.load_entries()
                entries_dict: dict[
                    str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
                ] = general_component.get_entries_dict(orientation)

                if general_component.get_under_label(orientation):
                    current_row += 1
                else:
                    current_column += 1

                total_row_spans += 1

                for entry_name in entries_dict:
                    entry_widget: QWidget = entries_dict[entry_name][0]
                    row_span: int = entries_dict[entry_name][1]
                    column_span: int = entries_dict[entry_name][2]
                    entries_dict[entry_name][3]
                    alignment: Qt.AlignmentFlag | None = entries_dict[
                        entry_name
                    ][4]
                    if alignment is None:
                        alignment = Qt.AlignmentFlag.AlignLeft

                    vert_file_layout.addWidget(
                        entry_widget,
                        current_row,
                        current_column,
                        row_span,
                        column_span,
                        alignment,
                    )  # type: ignore
                    current_row += row_span
        else:
            self._reset_layout(vert_file_layout)

            for name in components_dict:
                current_column: int = starting_column

                total_row_spans: int = 0

                general_component: MetadataComponent = components_dict[name]  # type: ignore

                general_component_qlabel: QLabel = (
                    general_component._component_qlabel
                )  # type: ignore
                hori_file_layout.addWidget(
                    general_component_qlabel, current_row, current_column, 1, 1
                )  # type: ignore

                general_component.load_entries()
                entries_dict: dict[
                    str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
                ] = general_component.get_entries_dict(orientation)  # type: ignore

                if general_component.get_under_label(orientation):
                    current_row += 1
                else:
                    current_column += 1

                total_row_spans += 1

                for entry_name in entries_dict:
                    entry_widget: QWidget = entries_dict[entry_name][0]
                    row_span: int = entries_dict[entry_name][1]
                    column_span: int = entries_dict[entry_name][2]
                    entries_dict[entry_name][3]
                    alignment: Qt.AlignmentFlag | None = entries_dict[
                        entry_name
                    ][4]
                    if alignment is None:
                        alignment = Qt.AlignmentFlag.AlignLeft

                    hori_file_layout.addWidget(
                        entry_widget,
                        current_row,
                        current_column,
                        row_span,
                        column_span,
                        alignment,
                    )
                    current_row += row_span

        for vert_file_layout_row in range(vert_file_layout.rowCount()):
            vert_file_layout.setRowStretch(vert_file_layout_row, 0)
        vert_file_layout.setRowStretch(vert_file_layout.rowCount(), 1)
        for vert_file_layout_column in range(vert_file_layout.columnCount()):
            vert_file_layout.setColumnStretch(vert_file_layout_column, 0)
        vert_file_layout.setColumnStretch(
            vert_file_layout.columnCount() - 1, 1
        )
        for hori_file_layout_row in range(hori_file_layout.rowCount()):
            hori_file_layout.setRowStretch(hori_file_layout_row, 1)
        for hori_file_layout_column in range(hori_file_layout.columnCount()):
            hori_file_layout.setColumnStretch(hori_file_layout_column, 0)
        hori_file_layout.setColumnStretch(hori_file_layout.columnCount(), 1)

    def _set_axis_metadata_orientation(self, orientation: str) -> None:
        starting_row: int = 0
        starting_column: int = 0
        current_row: int = starting_row

        vert_axis_layout: QGridLayout = self._vert_axis_metadata_layout
        vert_axis_layout.setVerticalSpacing(8)
        hori_axis_layout: QGridLayout = self._hori_axis_metadata_layout

        components: list[AxisComponentBase] = (
            self._axis_metadata_instance.components
        )

        spacer_places_list: list[int] = []

        max_vert_cols: int = 0
        max_hori_rows: int = 0

        if orientation == 'vertical':
            self._reset_layout(vert_axis_layout)

            for idx, component in enumerate(components):
                current_column: int = starting_column

                vert_axis_layout.addWidget(
                    component.component_label,
                    current_row,
                    current_column,
                    1,
                    1,
                )
                current_column += 1

                component.load_entries()

                for axis_index in range(component.num_axes):
                    setting_column = current_column
                    max_row_span: int = 0
                    col_span_sum: int = 0

                    for entry in component.get_layout_entries(axis_index):
                        for widget in entry.widgets:
                            widget.setSizePolicy(
                                QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding,
                            )
                            vert_axis_layout.addWidget(
                                widget,
                                current_row,
                                setting_column,
                                entry.row_span,
                                entry.col_span,
                            )
                        setting_column += entry.col_span
                        col_span_sum += entry.col_span
                        if entry.row_span > max_row_span:
                            max_row_span = entry.row_span

                    if col_span_sum > max_vert_cols:
                        max_vert_cols = col_span_sum

                    current_row += max_row_span

                # Separator between components (not after the last one)
                if idx < len(components) - 1:
                    spacer_places_list.append(current_row)
                    current_row += 3

        elif orientation == 'horizontal':
            self._reset_layout(hori_axis_layout)

            for idx, component in enumerate(components):
                current_column: int = starting_column
                current_row: int = starting_row

                adding_label_column = current_column
                current_row += 1

                component.load_entries()

                max_axis_col_spans: int = 0

                for axis_index in range(component.num_axes):
                    current_axis_col_sum: int = 0
                    setting_column = current_column
                    max_row_span: int = 0

                    for entry in component.get_layout_entries(axis_index):
                        for widget in entry.widgets:
                            widget.setSizePolicy(
                                QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding,
                            )
                            hori_axis_layout.addWidget(
                                widget,
                                current_row,
                                setting_column,
                                entry.row_span,
                                entry.col_span,
                            )
                        setting_column += entry.col_span
                        current_axis_col_sum += entry.col_span
                        if entry.row_span > max_row_span:
                            max_row_span = entry.row_span

                    if current_axis_col_sum > max_axis_col_spans:
                        max_axis_col_spans = current_axis_col_sum

                    current_row += max_row_span

                if current_row > max_hori_rows:
                    max_hori_rows = current_row

                component.component_label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                hori_axis_layout.addWidget(
                    component.component_label,
                    0,
                    adding_label_column,
                    1,
                    1,
                )

                # Separator between components (not after the last one)
                if idx < len(components) - 1:
                    spacer_places_list.append(
                        starting_column + max_axis_col_spans
                    )

                starting_column += max_axis_col_spans + 3

        for spacer_position in spacer_places_list:
            if orientation == 'vertical':
                before_spacer_item = QWidget()
                before_spacer_item.setFixedHeight(2)
                before_spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                vert_axis_layout.addWidget(
                    before_spacer_item,
                    spacer_position,
                    0,
                    1,
                    max_vert_cols + 1,
                )

                spacer_item = QFrame()
                spacer_item.setFrameShape(QFrame.Shape.HLine)
                spacer_item.setFrameShadow(QFrame.Shadow.Sunken)
                spacer_item.setStyleSheet(
                    'color: #999; background-color: #999;'
                )
                spacer_item.setFixedHeight(3)
                spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                vert_axis_layout.addWidget(
                    spacer_item, spacer_position + 1, 0, 1, max_vert_cols + 1
                )

                after_spacer_item = QWidget()
                after_spacer_item.setFixedHeight(2)
                after_spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                vert_axis_layout.addWidget(
                    after_spacer_item,
                    spacer_position + 2,
                    0,
                    1,
                    max_vert_cols + 1,
                )

            elif orientation == 'horizontal':
                before_spacer_item = QWidget()
                before_spacer_item.setFixedWidth(2)
                before_spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
                )
                hori_axis_layout.addWidget(
                    before_spacer_item,
                    0,
                    spacer_position,
                    max_hori_rows + 1,
                    1,
                )

                spacer_item = QFrame()
                spacer_item.setFrameShape(QFrame.Shape.VLine)
                spacer_item.setFrameShadow(QFrame.Shadow.Sunken)
                spacer_item.setStyleSheet(
                    'color: #999; background-color: #999;'
                )
                spacer_item.setFixedWidth(3)
                spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
                )
                hori_axis_layout.addWidget(
                    spacer_item, 0, spacer_position + 1, max_hori_rows + 1, 1
                )

                after_spacer_item = QWidget()
                after_spacer_item.setFixedWidth(2)
                after_spacer_item.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
                )
                hori_axis_layout.addWidget(
                    after_spacer_item,
                    0,
                    spacer_position + 2,
                    max_hori_rows + 1,
                    1,
                )

        if orientation == 'vertical':
            for row in range(vert_axis_layout.rowCount()):
                if row > current_row + 1:
                    vert_axis_layout.setRowMinimumHeight(row, 0)
                vert_axis_layout.setRowStretch(row, 0)
            vert_axis_layout.setRowStretch(current_row + 1, 1)
            for column in range(vert_axis_layout.columnCount()):
                if column > max_vert_cols:
                    vert_axis_layout.setColumnMinimumWidth(column, 0)
                vert_axis_layout.setColumnStretch(column, 0)
            vert_axis_layout.setColumnStretch(max_vert_cols, 1)
            vert_axis_layout.parentWidget().updateGeometry()
        else:
            for row in range(hori_axis_layout.rowCount()):
                if row > max_hori_rows + 1:
                    hori_axis_layout.setRowMinimumHeight(row, 0)
                hori_axis_layout.setRowStretch(row, 0)
            hori_axis_layout.setRowStretch(max_hori_rows + 1, 1)
            for column in range(hori_axis_layout.columnCount()):
                if column > starting_column - 2:
                    hori_axis_layout.setColumnMinimumWidth(column, 0)
                hori_axis_layout.setColumnStretch(column, 0)
            hori_axis_layout.setColumnStretch(starting_column - 2, 1)
            hori_axis_layout.parentWidget().updateGeometry()

    def _set_inheritance_orientation(self, orientation: str) -> None:
        vert_inheritance_layout: QGridLayout = self._vert_inheritance_layout
        vert_inheritance_layout.setVerticalSpacing(8)
        hori_inheritance_layout: QGridLayout = self._hori_inheritance_layout

        setting_layout: QGridLayout | None = None

        if orientation == 'vertical':
            self._reset_layout(vert_inheritance_layout)
            setting_layout = vert_inheritance_layout
        else:
            self._reset_layout(hori_inheritance_layout)
            setting_layout = hori_inheritance_layout

        setting_layout.addWidget(self._inheritance_instance)

    def _set_layout_type(self, layout_type: str) -> None:
        if layout_type == 'vertical':
            self._set_general_metadata_orientation('vertical')
            self._set_axis_metadata_orientation('vertical')
            self._set_inheritance_orientation('vertical')
        elif layout_type == 'horizontal':
            self._set_general_metadata_orientation('horizontal')
            self._set_axis_metadata_orientation('horizontal')
            self._set_inheritance_orientation('horizontal')

        current_layout: QStackedLayout = self._stacked_layout
        number_of_widgets: int = current_layout.count()
        for i in range(number_of_widgets):
            current_layout_widget: QWidget = current_layout.widget(i)
            if current_layout_widget is None:
                continue
            if current_layout_widget.container_orientation == layout_type:
                current_layout.setCurrentIndex(i)
                break

        self._current_orientation = layout_type

    def _resolve_show_inheritance_checkboxes(
        self, orientation: str, checked: bool
    ) -> None:
        if self._current_orientation == orientation:
            self._axis_metadata_instance.set_checkboxes_visible(checked)

    def apply_inheritance_to_current_layer(
        self, template_layer: Layer
    ) -> None:
        active_layer = resolve_layer(self._napari_viewer)
        if active_layer is None:
            return

        if active_layer.ndim != template_layer.ndim:
            show_info(
                'Inheritance layer must have same number of dimensions as current layer'
            )
            return

        for component in self._axis_metadata_instance.components:
            component.inherit_layer_properties(template_layer)
        if self._current_orientation == 'horizontal':
            self._set_layout_type('horizontal')
        else:
            self._set_layout_type('vertical')
