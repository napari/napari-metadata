from typing import TYPE_CHECKING, cast

import pint
from qtpy.QtCore import QObject, QSignalBlocker, Qt
from qtpy.QtGui import QShowEvent
from qtpy.QtWidgets import (
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from napari_metadata._collapsible_containers import (
    CollapsibleSectionContainer,
    HorizontalOnlyOuterScrollArea,
)
from napari_metadata._inheritance_widget import InheritanceWidget
from napari_metadata._model import (
    get_axes_labels,
    get_pint_ureg,
    get_axes_units,
    resolve_layer,
    set_axes_labels,
    set_axes_scales,
    set_axes_translations,
    set_axes_units,
)
from napari_metadata._space_units import SpaceUnits
from napari_metadata._time_units import TimeUnits
from napari_metadata._protocols import (
    AxesMetadataComponentsInstanceAPI,
    AxisComponent,
    MetadataComponent,
)
from napari_metadata._axis_metadata_widgets import (
    AxisMetadata,
    AxisLabels,
    AxisTranslations,
    AxisScales,
)
from napari_metadata._file_metadata_widgets import FileGeneralMetadata

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer
    from napari.utils.notifications import show_info


class MetadataWidget(QWidget):
    _selected_layer: 'Layer | None'
    _inheritance_layer: 'Layer | None'
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

    def __init__(self, napari_viewer: 'ViewerModel'):
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
        self._connect_file_general_metadata_components()

        self._vert_file_general_metadata_container: QWidget = QWidget()
        self._vert_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._vert_file_general_metadata_container.setLayout(
            self._vert_file_general_metadata_layout
        )
        self._hori_file_general_metadata_container: QWidget = QWidget()
        self._hori_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._hori_file_general_metadata_container.setLayout(
            self._hori_file_general_metadata_layout
        )

        self._axis_metadata_instance = AxisMetadata(napari_viewer, self)

        self._vert_axis_metadata_container: QWidget = QWidget()
        self._vert_axis_metadata_layout: QGridLayout = QGridLayout()
        self._vert_axis_metadata_container.setLayout(
            self._vert_axis_metadata_layout
        )
        self._hori_axis_metadata_container: QWidget = QWidget()
        self._hori_axis_metadata_layout: QGridLayout = QGridLayout()
        self._hori_axis_metadata_container.setLayout(
            self._hori_axis_metadata_layout
        )

        # self._inheritance_instance = AxesInheritance(napari_viewer, self)
        self._inheritance_instance: InheritanceWidget = InheritanceWidget(
            napari_viewer, self
        )

        self._vert_inheritance_container: QWidget = QWidget()
        self._vert_inhertiance_layout: QGridLayout = QGridLayout()
        self._vert_inheritance_container.setLayout(
            self._vert_inhertiance_layout
        )
        self._hori_inheritance_container: QWidget = QWidget()
        self._hori_inheritance_layout: QGridLayout = QGridLayout()
        self._hori_inheritance_container.setLayout(
            self._hori_inheritance_layout
        )

        vertical_container: QScrollArea = QScrollArea()
        vertical_container.setWidgetResizable(True)
        vertical_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        vertical_container.container_orientation = 'vertical'

        vertical_content = QWidget()
        vertical_content.setLayout(self._vertical_layout)
        vertical_container.setWidget(vertical_content)

        self._stacked_layout.addWidget(vertical_container)

        self._collapsible_vertical_file_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'vertical_file_metadata',
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
            orientation='vertical',
        )
        self._collapsible_vertical_editable_metadata._set_button_text(
            'Axes metadata'
        )
        self._collapsible_vertical_editable_metadata._set_expanding_area_widget(
            self._vert_axis_metadata_container
        )

        self._collapsible_vertical_inheritance: CollapsibleSectionContainer = (
            CollapsibleSectionContainer(
                self._napari_viewer,
                'vertical_inheritance',
                orientation='vertical',
            )
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
            HorizontalOnlyOuterScrollArea()
        )
        horizontal_container.setWidgetResizable(True)
        horizontal_container.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        horizontal_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        horizontal_container.container_orientation = 'horizontal'

        horizontal_content: QWidget = QWidget()
        horizontal_content.setLayout(self._horizontal_layout)
        horizontal_container.setWidget(horizontal_content)
        self._stacked_layout.addWidget(horizontal_container)

        self._collapsible_horizontal_file_metadata: CollapsibleSectionContainer = CollapsibleSectionContainer(
            self._napari_viewer,
            'horizontal_file_metadata',
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
            orientation='horizontal',
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

        no_layer_container: QWidget = QWidget()
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
        general_metadata_components: dict[str, MetadataComponent] = (
            general_metadata_instance._file_metadata_components_dict
        )  # type: ignore
        general_metadata_component: MetadataComponent
        for general_metadata_component in general_metadata_components.values():
            general_metadata_component.load_entries()

    def _disconnect_layer_params(self, layer: 'Layer') -> None:
        layer.events.name.disconnect(self._on_selected_layer_name_changed)

    def _connect_layer_params(self, layer: 'Layer') -> None:
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

    def showEvent(self, a0: QShowEvent | None) -> None:
        if self._already_shown:
            return

        super().showEvent(a0)

        parent_widget = self.parent()
        if parent_widget is None:
            return
        if isinstance(parent_widget, QDockWidget):
            napari_viewer: ViewerModel = self._viewer
            if napari_viewer is None:
                return
            napari_viewer = cast('ViewerModel', napari_viewer)
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

        axis_meta_instance: AxisMetadata = self._axis_metadata_instance
        components_dict = axis_meta_instance._axis_metadata_components_dict  # type: ignore

        spacer_places_list: list[int] = []

        max_vert_cols: int = 0
        max_hori_rows: int = 0

        if orientation == 'vertical':
            self._reset_layout(vert_axis_layout)

            # This is the name of every axis
            for name in components_dict:
                current_column: int = starting_column

                # This is the instance of the Axis Protocol
                axis_component: AxisComponent = components_dict[name]  # type: ignore

                axis_component_qlabel: QLabel = (
                    axis_component._component_qlabel
                )  # type: ignore
                vert_axis_layout.addWidget(
                    axis_component_qlabel, current_row, current_column, 1, 1
                )  # type: ignore

                current_column += 1

                axis_component.load_entries()
                ## TODO: After adding the entries, they need to be connected because of the creating of the axis widgets from scratch when the layer changes.
                # Probably better to call it from within the AxisComponent class because I don't know if they're created or not by this point.
                entries_dict: dict[
                    int,
                    dict[
                        str,
                        tuple[
                            list[QWidget],
                            int,
                            int,
                            str,
                            Qt.AlignmentFlag | None,
                        ],
                    ],
                ] = axis_component.get_entries_dict()

                for axis_index in entries_dict:
                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[
                        str,
                        tuple[
                            list[QWidget],
                            int,
                            int,
                            str,
                            Qt.AlignmentFlag | None,
                        ],
                    ] = entries_dict[axis_index]  # type: ignore

                    sum_of_column_spans: int = 0

                    for widget_name in axis_entries_dict:
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[
                            widget_name
                        ][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft
                        for entry_widget in axis_entries_dict[widget_name][0]:
                            entry_widget.setSizePolicy(
                                QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding,
                            )
                            vert_axis_layout.addWidget(
                                entry_widget,
                                current_row,
                                setting_column,
                                row_span,
                                column_span,
                            )
                        setting_column += column_span
                        sum_of_column_spans += column_span
                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span

                    if sum_of_column_spans > max_vert_cols:
                        max_vert_cols = sum_of_column_spans

                    current_row += max_axis_index_row_span

                # if it is not the last axis:
                if name != list(components_dict.keys())[-1]:
                    spacer_places_list.append(current_row)
                    current_row += 3

        elif orientation == 'horizontal':
            self._reset_layout(hori_axis_layout)

            # This is the name of every axis
            for name in components_dict:
                current_column: int = starting_column
                current_row: int = starting_row

                # This is the instance of the Axis Protocol
                axis_component: AxisComponent = components_dict[name]  # type: ignore

                axis_component_qlabel: QLabel = (
                    axis_component._component_qlabel
                )  # type: ignore
                axis_component_qlabel.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )  # type: ignore
                adding_label_column = current_column

                current_row += 1

                axis_component.load_entries()
                ## TODO: After adding the entries, they need to be connected because of the creating of the axis widgets from scratch when the layer changes.
                # Probably better to call it from within the AxisComponent class because I don't know if they're created or not by this point.
                entries_dict: dict[
                    int,
                    dict[
                        str,
                        tuple[
                            list[QWidget],
                            int,
                            int,
                            str,
                            Qt.AlignmentFlag | None,
                        ],
                    ],
                ] = axis_component.get_entries_dict()

                max_axis_col_spans: int = 0

                for axis_index in entries_dict:
                    current_axis_col_sum: int = 0

                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[
                        str,
                        tuple[
                            list[QWidget],
                            int,
                            int,
                            str,
                            Qt.AlignmentFlag | None,
                        ],
                    ] = entries_dict[axis_index]  # type: ignore

                    for widget_name in axis_entries_dict:
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[
                            widget_name
                        ][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft

                        for entry_widget in axis_entries_dict[widget_name][0]:
                            entry_widget.setSizePolicy(
                                QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding,
                            )
                            hori_axis_layout.addWidget(
                                entry_widget,
                                current_row,
                                setting_column,
                                row_span,
                                column_span,
                            )
                        setting_column += column_span
                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span

                        current_axis_col_sum += column_span

                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span

                    if current_axis_col_sum > max_axis_col_spans:
                        max_axis_col_spans = current_axis_col_sum

                    current_row += max_axis_index_row_span

                if current_row > max_hori_rows:
                    max_hori_rows = current_row

                hori_axis_layout.addWidget(
                    axis_component_qlabel, 0, adding_label_column, 1, 1
                )  # type: ignore

                ## if it is not the last axis:
                if name != list(components_dict.keys())[-1]:
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
        vert_inheritance_layout: QGridLayout = self._vert_inhertiance_layout
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

    def _connect_file_general_metadata_components(self) -> None:
        file_general_meta_instance: FileGeneralMetadata = (
            self._general_metadata_instance
        )
        components_dict = (
            file_general_meta_instance._file_metadata_components_dict
        )  # type: ignore

        for name in components_dict:
            general_component: MetadataComponent = components_dict[name]  # type: ignore
            entries_dict: dict[str, tuple[QWidget, int, int, str]] = (
                general_component.get_entries_dict(self._current_orientation)
            )
            for entry_name in entries_dict:
                entry_widget: QWidget = entries_dict[entry_name][0]
                method_name: str = entries_dict[entry_name][3]
                if method_name == '':
                    continue
                if isinstance(entry_widget, QLineEdit):
                    entry_line_edit: QLineEdit = cast(QLineEdit, entry_widget)
                    entry_line_edit.textEdited.connect(
                        getattr(self, method_name)
                    )

    def get_axes_metadata_instance(self) -> AxesMetadataComponentsInstanceAPI:
        axes_metadata_api: AxesMetadataComponentsInstanceAPI = cast(
            AxesMetadataComponentsInstanceAPI, self._axis_metadata_instance
        )
        return axes_metadata_api

    def _on_name_line_changed(self, text: str) -> None:
        return

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

    def connect_axis_components(self, component: MetadataComponent) -> None:
        component_entries: dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ] = component.get_entries_dict('vertical')  # type: ignore

        for axis_number in component_entries:
            for component_name in component_entries[axis_number]:
                method_str: str = component_entries[axis_number][
                    component_name
                ][3]
                if method_str == '':
                    continue
                widget: QWidget = component_entries[axis_number][
                    component_name
                ][0]
                calling_method = None
                try:
                    calling_method = getattr(self, method_str)
                except AttributeError:
                    continue
                if isinstance(widget, QLineEdit):
                    line_edit_widget: QLineEdit = cast(QLineEdit, widget)
                    line_edit_widget.textEdited.connect(calling_method)
                if isinstance(widget, QDoubleSpinBox):
                    spin_double_box: QDoubleSpinBox = cast(
                        QDoubleSpinBox, widget
                    )
                    spin_double_box.valueChanged.connect(calling_method)
                if isinstance(widget, QComboBox):
                    combo_box: QComboBox = cast(QComboBox, widget)
                    combo_box.currentIndexChanged.connect(calling_method)

    def _on_axis_labels_lines_edited(self) -> None:
        axes_labels_component: AxisLabels = (
            self._axis_metadata_instance._axis_metadata_components_dict[
                'AxisLabels'
            ]
        )  # type: ignore
        axes_tuples: tuple[str, ...] = (
            axes_labels_component.get_line_edit_labels()
        )  # type: ignore
        set_axes_labels(self._viewer, axes_tuples)  # type: ignore
        for (
            axes_component_name
        ) in self._axis_metadata_instance._axis_metadata_components_dict:
            if axes_component_name != 'AxisLabels':
                axis_component: MetadataComponent = self._axis_metadata_instance._axis_metadata_components_dict[
                    axes_component_name
                ]  # type: ignore
                for axis_number in range(
                    len(axis_component._axis_name_labels_tuple)
                ):
                    with QSignalBlocker(
                        axis_component._axis_name_labels_tuple[axis_number]
                    ):
                        axis_component._axis_name_labels_tuple[
                            axis_number
                        ].setText(axes_tuples[axis_number])
                        if axes_tuples[axis_number] == '':
                            axis_component._axis_name_labels_tuple[
                                axis_number
                            ].setText(f'{axis_number}')

    def _on_axis_translate_spin_box_adjusted(self) -> None:
        axes_translate_component: AxisTranslations = (
            self._axis_metadata_instance._axis_metadata_components_dict[
                'AxisTranslations'
            ]
        )  # type: ignore
        axes_tuples: tuple[float, ...] = (
            axes_translate_component.get_spin_box_values()
        )  # type: ignore
        set_axes_translations(self._viewer, axes_tuples)  # type: ignore

    def _on_axis_scale_spin_box_adjusted(self) -> None:
        axes_scale_component: AxisScales = (
            self._axis_metadata_instance._axis_metadata_components_dict[
                'AxisScales'
            ]
        )  # type: ignore
        axes_tuples: tuple[float, ...] = (
            axes_scale_component.get_spin_box_values()
        )  # type: ignore
        axis_scales_list: list[float] = []
        bad_number: bool = False
        for scale_tuple_index in range(len(axes_tuples)):  # type: ignore
            if axes_tuples[scale_tuple_index] <= 0:
                axis_scales_list.append(0.001)
                bad_number = True
                continue
            else:
                axis_scales_list.append(axes_tuples[scale_tuple_index])  # type: ignore
        if bad_number:
            spin_boxes_tuple: tuple[QDoubleSpinBox, ...] = (
                axes_scale_component._scale_spinbox_tuple
            )  # type: ignore
            for spin_box_index in range(len(spin_boxes_tuple)):  # type: ignore
                with QSignalBlocker(spin_boxes_tuple[spin_box_index]):  # type: ignore
                    spin_boxes_tuple[spin_box_index].setValue(
                        axis_scales_list[spin_box_index]
                    )  # type: ignore
            set_axes_scales(self._viewer, axis_scales_list)  # type: ignore
            return
        set_axes_scales(self._viewer, axes_tuples)  # type: ignore

    def _on_type_combobox_changed(self) -> None:
        unit_axis_component: MetadataComponent = (
            self._axis_metadata_instance._axis_metadata_components_dict[
                'AxisUnits'
            ]
        )  # type: ignore
        type_combobox_tuple: tuple[QComboBox, ...] = (
            unit_axis_component._type_combobox_tuple
        )  # type: ignore
        unit_combobox_tuple: tuple[QComboBox, ...] = (
            unit_axis_component._unit_combobox_tuple
        )  # type: ignore
        current_units: tuple[pint.Unit | str, ...] = get_axes_units(
            self._napari_viewer, self._selected_layer
        )
        unit_registry: pint.registry.ApplicationRegistry = get_pint_ureg()
        for axis_number in range(len(type_combobox_tuple)):  # type: ignore
            unit_string: str = unit_combobox_tuple[axis_number].currentText()  # type: ignore
            type_string: str = type_combobox_tuple[axis_number].currentText()  # type: ignore
            if (
                type_string == 'space'
                and unit_string not in SpaceUnits.names()
            ):
                with QSignalBlocker(unit_combobox_tuple[axis_number]):  # type: ignore
                    unit_combobox_tuple[axis_number].clear()  # type: ignore
                    unit_combobox_tuple[axis_number].addItems(
                        SpaceUnits.names()
                    )  # type: ignore
                    unit_combobox_tuple[axis_number].setCurrentIndex(
                        unit_combobox_tuple[axis_number].findText('pixel')
                    )  # type: ignore
            elif (
                type_string == 'time' and unit_string not in TimeUnits.names()
            ):
                with QSignalBlocker(unit_combobox_tuple[axis_number]):  # type: ignore
                    unit_combobox_tuple[axis_number].clear()  # type: ignore
                    unit_combobox_tuple[axis_number].addItems(
                        TimeUnits.names()
                    )  # type: ignore
                    unit_combobox_tuple[axis_number].setCurrentIndex(
                        unit_combobox_tuple[axis_number].findText('second')
                    )  # type: ignore
            else:
                with QSignalBlocker(unit_combobox_tuple[axis_number]):  # type: ignore
                    unit_combobox_tuple[axis_number].clear()  # type: ignore
                    unit_combobox_tuple[axis_number].addItems(
                        SpaceUnits.names()
                    )  # type: ignore
                    unit_combobox_tuple[axis_number].addItems(
                        TimeUnits.names()
                    )  # type: ignore
                    unit_combobox_tuple[axis_number].setCurrentIndex(
                        unit_combobox_tuple[axis_number].findText(unit_string)
                    )  # type: ignore

        setting_units_list: list[pint.Unit | str | None] = []
        for axis_number in range(len(unit_combobox_tuple)):
            unit_string: str = unit_combobox_tuple[axis_number].currentText()  # type: ignore
            unit_pint: pint.Unit | None
            if unit_string == 'none':
                unit_pint = None
            else:
                unit_pint = unit_registry.Unit(unit_string)
            setting_units_list.append(unit_pint)
        set_axes_units(self._napari_viewer, setting_units_list)  # type: ignore

    def _on_unit_combobox_changed(self) -> None:
        unit_axis_component: MetadataComponent = (
            self._axis_metadata_instance._axis_metadata_components_dict[
                'AxisUnits'
            ]
        )  # type: ignore
        unit_combobox_tuple: tuple[QComboBox, ...] = (
            unit_axis_component._unit_combobox_tuple
        )  # type: ignore
        type_combobox_tuple: tuple[QComboBox, ...] = (
            unit_axis_component._type_combobox_tuple
        )  # type: ignore
        current_units: tuple[pint.Unit | str, ...] = get_axes_units(
            self._napari_viewer, self._selected_layer
        )
        unit_registry: pint.registry.ApplicationRegistry = get_pint_ureg()
        setting_units_list: list[pint.Unit | str | None] = []
        for axis_number in range(len(unit_combobox_tuple)):  # type: ignore
            unit_string: str = unit_combobox_tuple[axis_number].currentText()  # type: ignore
            if unit_string in SpaceUnits.names():
                with QSignalBlocker(type_combobox_tuple[axis_number]):  # type: ignore
                    type_combobox_tuple[axis_number].setCurrentIndex(
                        type_combobox_tuple[axis_number].findText('space')
                    )  # type: ignore
            elif unit_string in TimeUnits.names():
                with QSignalBlocker(type_combobox_tuple[axis_number]):  # type: ignore
                    type_combobox_tuple[axis_number].setCurrentIndex(
                        type_combobox_tuple[axis_number].findText('time')
                    )  # type: ignore
            else:
                with QSignalBlocker(type_combobox_tuple[axis_number]):  # type: ignore
                    type_combobox_tuple[axis_number].setCurrentIndex(
                        type_combobox_tuple[axis_number].findText('string')
                    )  # type: ignore
            unit_pint: pint.Unit | None
            if unit_string == 'none' or not unit_string:
                unit_pint = None
            else:
                unit_pint = unit_registry.Unit(unit_string)
            setting_units_list.append(unit_pint)
        set_axes_units(self._napari_viewer, setting_units_list)  # type: ignore

    def apply_inheritance_to_current_layer(
        self, template_layer: 'Layer'
    ) -> None:
        active_layer = resolve_layer(self._napari_viewer)
        if active_layer is None:
            return

        if active_layer.ndim != template_layer.ndim:
            show_info(
                'Inheritance layer must have same number of dimensions as current layer'
            )
            return

        axis_component: AxisComponent
        for axis_component in self._axis_metadata_instance._axis_metadata_components_dict.values():
            axis_component.inherit_layer_properties(template_layer)
        if self._current_orientation == 'horizontal':
            self._set_layout_type('horizontal')
        else:
            self._set_layout_type('vertical')
