from typing import TYPE_CHECKING, Protocol, cast

import pint
from qtpy.QtCore import QObject, QRect, QSignalBlocker, QSize, Qt
from qtpy.QtGui import QFontMetrics, QPainter, QShowEvent
from qtpy.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
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
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QStyle,
    QStyleOptionButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from napari_metadata._axis_type import AxisType
from napari_metadata._file_size import generate_display_size
from napari_metadata._model import (
    get_active_layer,
    get_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_dimensions,
    get_layer_source_path,
    set_active_layer_axes_labels,
    set_active_layer_axes_scales,
    set_active_layer_axes_translations,
    set_active_layer_axes_units,
)
from napari_metadata._space_units import SpaceUnits
from napari_metadata._time_units import TimeUnits

from napari_metadata._vertical_containers import VerticalSectionContainer
from napari_metadata._horizontal_containers import HorizontalSectionContainer

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer
    from napari.utils.notifications import show_info

INHERIT_STRING = 'Inherit'

"""This protocol is made to store the general metadata components that are not the axis components. They differn from the axis components
because they only get one widget per entry and I didn't wanto to complicate (complicate more) the extension patterns so it'll have to stay like this.
It might be best if the plugin won't allow the user to modify any of these except for the layer name.
NOTE: It is 100% possible to integrate them into a single type of component by passing lists instead of single values in the get_entries_dict but It might get too complex to extend?"""


class MetadataComponent(Protocol):
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _component_qlabel: QLabel
    SUBMENU: str

    """All general metadata components should pass the napari viewer and the main widget (This is the MetaDataWidget that isn't declared until later... SOMEBODY
    SHOULD MAKE A PROTOCOL FOR THIS....). This is to make sure that the components can call methods from the MetaDataWidget in case they need to interact between components."""

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None: ...

    """I am suggesting the load_entries method to update/load anything that the component needs to display the information."""

    def load_entries(self, layer: 'Layer | None' = None) -> None: ...

    """ This method returns the dictionary that will be used to populate the general metadata QGridLayout.
    It requires you to input the type of layout, either horizontal or vertical, with vertical set to default.
    It should return a dictionary with the name of the entries as keys (They'll be set in bold capital letters) and a tuple with the corresponding
    QWidget, the row span, the column span, the calling method as a string or none if there's no method """

    def get_entries_dict(
        self, layout_mode: str
    ) -> (
        dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
        | dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ]
    ): ...

    """ This method returns a boolean that will determine if the entry is to the left or below the name of the entry. """

    def get_under_label(self, layout_mode: str) -> bool: ...


METADATA_COMPONENTS_DICT: dict[str, type[MetadataComponent]] = {}

""" This decorator is used to register the MetadataComponent class in the METADATA_COMPONENTS_DICT dictionary."""


def _metadata_component(
    _setting_class: type[MetadataComponent],
) -> type[MetadataComponent]:
    METADATA_COMPONENTS_DICT[_setting_class.__name__] = _setting_class
    return _setting_class


@_metadata_component
class LayerNameComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'GeneralMetadata'

    _layer_name_line_edit: QLineEdit

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel('Layer Name:')
        component_qlabel.setStyleSheet('font-weight: bold;')  # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel

        layer_name_line_edit = QLineEdit()
        self._layer_name_line_edit = layer_name_line_edit
        layer_name_line_edit.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )
        self._component_name = 'LayerName'

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            self._layer_name_line_edit.setText('None selected')  # type: ignore
            return
        self._layer_name_line_edit.setText(active_layer.name)  # type: ignore

    def get_entries_dict(
        self, layout_mode: str = 'vertical'
    ) -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[
            str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
        ] = {}
        if layout_mode == 'vertical':
            returning_dict['LayerName'] = (
                self._layer_name_line_edit,
                1,
                2,
                '_on_name_line_changed',
                Qt.AlignmentFlag.AlignTop,
            )  # type: ignore
        else:
            returning_dict['LayerName'] = (
                self._layer_name_line_edit,
                1,
                3,
                '_on_name_line_changed',
                Qt.AlignmentFlag.AlignTop,
            )  # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = 'vertical') -> bool:
        return layout_mode == 'vertical'


@_metadata_component
class LayerShapeComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'GeneralMetadata'

    _layer_shape_label: QLabel

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel('Layer Shape:')
        component_qlabel.setStyleSheet('font-weight: bold;')  # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel

        shape_label: QLabel = QLabel('None selected')
        shape_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_shape_label = shape_label

        self._component_name = 'LayerShape'

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            self._layer_shape_label.setText('None selected')  # type: ignore
            return
        self._layer_shape_label.setText(
            str(get_layer_data_shape(active_layer))
        )  # type: ignore

    def get_entries_dict(
        self, layout_mode: str = 'vertical'
    ) -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[
            str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
        ] = {}
        if layout_mode == 'vertical':
            returning_dict['LayerShape'] = (
                self._layer_shape_label,
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        else:
            returning_dict['LayerShape'] = (
                self._layer_shape_label,
                1,
                2,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = 'vertical') -> bool:
        return False


@_metadata_component
class LayerDataTypeComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'GeneralMetadata'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel('Layer DataType:')
        component_qlabel.setStyleSheet('font-weight: bold;')  # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel

        data_type_label: QLabel = QLabel('None selected')
        data_type_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_data_type_label = data_type_label

        self._component_name = 'LayerDataType'

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            self._layer_data_type_label.setText('None selected')  # type: ignore
            return
        self._layer_data_type_label.setText(
            str(get_layer_data_dtype(active_layer))
        )  # type: ignore

    def get_entries_dict(
        self, layout_mode: str = 'vertical'
    ) -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[
            str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
        ] = {}
        if layout_mode == 'vertical':
            returning_dict['LayerDataType'] = (
                self._layer_data_type_label,
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        else:
            returning_dict['LayerDataType'] = (
                self._layer_data_type_label,
                1,
                2,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = 'vertical') -> bool:
        return False


@_metadata_component
class LayerFileSizeComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'GeneralMetadata'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel('File Size:')
        component_qlabel.setStyleSheet('font-weight: bold;')  # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel

        file_size_label: QLabel = QLabel('None selected')
        file_size_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_file_size_label = file_size_label

        self._component_name = 'LayerFileSize'

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            self._layer_file_size_label.setText('None selected')  # type: ignore
            return
        self._layer_file_size_label.setText(
            str(generate_display_size(active_layer))
        )  # type: ignore

    def get_entries_dict(
        self, layout_mode: str = 'vertical'
    ) -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[
            str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
        ] = {}
        if layout_mode == 'vertical':
            returning_dict['LayerFileSize'] = (
                self._layer_file_size_label,
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        else:
            returning_dict['LayerFileSize'] = (
                self._layer_file_size_label,
                1,
                2,
                '',
                Qt.AlignmentFlag.AlignLeft,
            )  # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = 'vertical') -> bool:
        return False


@_metadata_component
class SourcePathComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'GeneralMetadata'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._component_name = 'SourcePath'
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel('Source Path:')
        component_qlabel.setStyleSheet('font-weight: bold;')  # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel

        source_path_text_edit: SingleLineTextEdit = SingleLineTextEdit()
        source_path_text_edit.setPlainText('None selected')
        source_path_text_edit.setReadOnly(True)
        source_path_text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        source_path_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._source_path_text_edit = source_path_text_edit

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            self._source_path_text_edit.setPlainText('None selected')  # type: ignore
            font_metrics = QFontMetrics(self._source_path_text_edit.font())
            self._source_path_text_edit.setMaximumHeight(
                font_metrics.height() + 30
            )
            return
        self._source_path_text_edit.setPlainText(
            str(get_layer_source_path(active_layer))
        )  # type: ignore
        font_metrics = QFontMetrics(self._source_path_text_edit.font())
        self._source_path_text_edit.setMaximumHeight(
            font_metrics.height() + 30
        )

    def get_entries_dict(
        self, layout_mode: str = 'vertical'
    ) -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[
            str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]
        ] = {}
        if layout_mode == 'vertical':
            returning_dict['SourcePath'] = (
                self._source_path_text_edit,
                1,
                2,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )  # type: ignore
        else:
            returning_dict['SourcePath'] = (
                self._source_path_text_edit,
                1,
                3,
                '',
                Qt.AlignmentFlag.AlignTop,
            )  # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = 'vertical') -> bool:
        return layout_mode == 'vertical'


""" This is the class that integrates all of the general metadata components together and instantiates them. This class itself
is instantiated in the MetadataWidget class, which is ultimately the main class passed to napari. This class will only hold the
components instances and everything else is handled in the MetadataWidget class or the individual metadata component classes."""


class FileGeneralMetadata:
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _file_metadata_components_dict: dict[str, MetadataComponent]

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        self._file_metadata_components_dict: dict[str, MetadataComponent] = {}

        for (
            metadata_comp_name,
            metadata_component_class,
        ) in METADATA_COMPONENTS_DICT.items():
            if metadata_component_class.SUBMENU == 'GeneralMetadata':
                self._file_metadata_components_dict[metadata_comp_name] = (
                    metadata_component_class(napari_viewer, main_widget)
                )


class SingleLineTextEdit(QTextEdit):
    def sizeHint(self):
        font_metrics = QFontMetrics(self.font())
        return QSize(50, font_metrics.height())

    def maximumHeight(self) -> int:
        font_metrics = QFontMetrics(self.font())
        return font_metrics.height() + 6


class FileMetadataWidget(QWidget):
    _widget_parent: QWidget | None
    _layout: QVBoxLayout

    _active_listeners: bool

    def __init__(
        self, viewer: 'ViewerModel', parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._viewer = viewer
        self._widget_parent = parent
        layout = QVBoxLayout()
        self._layout = layout
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._layout.setSpacing(5)
        self.setLayout(layout)
        self._active_listeners = False

        layer_name_label: QLabel = QLabel('Layer name:')
        layer_name_label.setStyleSheet('font-weight: bold;')
        self._layer_name_label: QLabel = layer_name_label
        self._layout.addWidget(self._layer_name_label)

        self._layer_name_QLineEdit = QLineEdit()
        self._layer_name_QLineEdit.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )
        self._layer_name_QLineEdit.setReadOnly(False)

        self._layout.addWidget(self._layer_name_QLineEdit)

        self._layer_data_shape_label = QLabel('Data shape:')
        self._layer_data_shape_label.setStyleSheet('font-weight: bold;')
        self._layer_data_shape_label.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
            )
        )

        self._layer_data_shape = QLabel('None selected')
        self._layer_data_shape.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )

        shape_container: QWidget = QWidget()
        shape_layout: QHBoxLayout = QHBoxLayout(shape_container)
        shape_layout.setContentsMargins(0, 0, 0, 0)
        shape_layout.addWidget(self._layer_data_shape_label)
        shape_layout.addWidget(self._layer_data_shape)
        shape_layout.addStretch(1)

        self._layer_data_type_label = QLabel('Data type:')
        self._layer_data_type_label.setStyleSheet('font-weight: bold;')
        self._layer_data_type_label.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
            )
        )

        self._layer_data_type = QLabel('None selected')
        self._layer_data_type.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )

        type_container: QWidget = QWidget()
        type_layout: QHBoxLayout = QHBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.addWidget(self._layer_data_type_label)
        type_layout.addWidget(self._layer_data_type)
        type_layout.addStretch(1)

        self._layer_file_size = QLabel('None selected')
        self._layer_file_size.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )

        self._layer_file_size_label = QLabel('File size:')
        self._layer_file_size_label.setStyleSheet('font-weight: bold;')
        self._layer_file_size_label.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
            )
        )

        size_container: QWidget = QWidget()
        size_layout: QHBoxLayout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.addWidget(self._layer_file_size_label)
        size_layout.addWidget(self._layer_file_size)
        size_layout.addStretch(1)

        self._layout.addWidget(shape_container)
        self._layout.addWidget(type_container)
        self._layout.addWidget(size_container)

        self._layer_path_label = QLabel('Source path:')
        self._layer_path_label.setStyleSheet('font-weight: bold;')
        self._layout.addWidget(self._layer_path_label)

        self._layer_path_line_edit = QLabel()
        # self._layer_path_line_edit.setReadOnly(False)
        self._layer_path_line_edit.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        )

        paht_container = QWidget()
        path_layout = QHBoxLayout(paht_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self._layer_path_line_edit)

        self._layer_path_scroll_area = QScrollArea()
        self._layer_path_scroll_area.setContentsMargins(0, 0, 0, 0)
        self._layer_path_scroll_area.setMaximumHeight(45)
        self._layer_path_scroll_area.setWidgetResizable(True)
        self._layer_path_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self._layer_path_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._layer_path_scroll_area.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )
        self._layer_path_scroll_area.setFrameShape(QFrame.NoFrame)  # type: ignore
        self._layer_path_scroll_area.setWidget(paht_container)
        self._layout.addWidget(self._layer_path_scroll_area)

        self._layout.addStretch(1)

    def _set_active_listeners(self, active_listeners: bool) -> None:
        self._active_listeners = active_listeners

    def _set_layer(self, layer: 'Layer | None') -> None:
        if layer is None:
            self._layer_name_QLineEdit.setText('None selected')
            self._layer_path_line_edit.setText('None selected')
            self._layer_data_shape.setText('None selected')
            self._layer_data_type.setText('None selected')
            self._layer_file_size.setText('None selected')
            return

        self._layer_name_QLineEdit.setText(layer.name)
        self._layer_path_line_edit.setText(layer.source.path)

        data_shape: tuple[int, ...] = get_layer_data_shape(layer)
        self._layer_data_shape.setText(f'{data_shape}')

        data_type: str = get_layer_data_dtype(layer)
        self._layer_data_type.setText(f'{data_type}')

        file_size: str = generate_display_size(layer)
        self._layer_file_size.setText(f'{file_size}')

    def _set_name(self, name: str) -> None:
        self._layer_name_QLineEdit.setText(name)

    def _set_path(self, path: str) -> None:
        self._layer_path_line_edit.setText(path)

    def _set_data_shape(self, data_shape: str) -> None:
        self._layer_data_shape.setText(data_shape)

    def _set_data_type(self, data_type: str) -> None:
        self._layer_data_type.setText(data_type)

    def _set_file_size(self, file_size: str) -> None:
        self._layer_file_size.setText(file_size)


""" This protocol is used to define the structure of the AxisComponent class.
NOTE: Again, it is possible to integrate the metadata into a single type of component by passing lists instead of single values in the get_entries_dict,
but it might complicate even more the already complicated extension patterns."""


class AxisComponent(Protocol):
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: 'ViewerModel'

    def __init__(self, napari_viewer: 'ViewerModel') -> None: ...
    def load_entries(
        self,
    ) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None: ...
    def get_entries_dict(
        self,
    ) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]: ...
    def get_rows_and_column_spans(self) -> dict[str, int] | None: ...
    def get_checkboxes_list(self) -> list[QCheckBox]: ...
    def inherit_layer_properties(self, template_layer: 'Layer') -> None: ...


AXES_ENTRIES_DICT: dict[str, type[AxisComponent]] = {}


@_metadata_component
class AxisLabels:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'AxisMetadata'

    _index_labels_tuple: tuple[QLabel, ...]
    _name_line_edit_tuple: tuple[QLineEdit, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]

    _NAME_LINE_EDIT_CALLING_METHOD = '_on_axis_labels_lines_edited'

    _selected_layer: 'Layer | None'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._component_name = 'AxisLabels'
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel('Labels:')
        component_qlabel.setStyleSheet('font-weight: bold')
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._index_labels_tuple = ()
        self._name_line_edit_tuple = ()
        self._inherit_checkbox_tuple = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_labels = get_axes_labels(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_labels)):
            with QSignalBlocker(self._name_line_edit_tuple[i]):
                self._name_line_edit_tuple[i].setText(layer_labels[i])

    def get_entries_dict(
        self, layout_mode: str
    ) -> dict[
        int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
    ]:
        returning_dict: dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ] = {}
        for i in range(len(self._index_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['index_label'] = (
                self._index_labels_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['name_line_edit'] = (
                self._name_line_edit_tuple[i],
                1,
                1,
                self._NAME_LINE_EDIT_CALLING_METHOD,
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                self._inherit_checkbox_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def get_line_edit_labels(self) -> tuple[str, ...]:
        return tuple(
            self._name_line_edit_tuple[i].text()
            for i in range(len(self._name_line_edit_tuple))
        )

    def _reset_tuples(self) -> None:
        (
            self._index_labels_tuple,
            self._name_line_edit_tuple,
            self._inherit_checkbox_tuple,
        ) = _reset_widget_tuples(
            cast(tuple[QWidget, ...], self._index_labels_tuple),
            cast(tuple[QWidget, ...], self._name_line_edit_tuple),
            cast(tuple[QWidget, ...], self._inherit_checkbox_tuple),
        )

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_index_tuple: tuple[QLabel, ...] = ()
        setting_name_tuple: tuple[QLineEdit, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        layer_labels: tuple[str, ...] = get_axes_labels(
            self._napari_viewer, layer
        )  # type: ignore
        for i in range(layer_dimensions):
            index_label: QLabel = QLabel(f'{i}')
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setting_index_tuple += (index_label,)
            name_line_edit: QLineEdit = QLineEdit()
            name_line_edit.setText(layer_labels[i])
            setting_name_tuple += (name_line_edit,)
        self._index_labels_tuple = setting_index_tuple
        self._name_line_edit_tuple = setting_name_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        main_widget: MetadataWidget = self._main_widget  # type: ignore
        main_widget.connect_axis_components(self)

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = get_active_layer(self._napari_viewer)
        if current_layer is None:
            return
        current_layer_labels: tuple[str, ...] = get_axes_labels(
            self._napari_viewer, current_layer
        )  # type: ignore
        template_labels: tuple[str, ...] = get_axes_labels(
            self._napari_viewer, template_layer
        )  # type: ignore
        setting_labels: list[str] = []
        checkbox_list: tuple[QCheckBox, ...] = self._inherit_checkbox_tuple
        for i in range(len(checkbox_list)):
            if checkbox_list[i].isChecked():
                setting_labels.append(template_labels[i])
            else:
                setting_labels.append(current_layer_labels[i])
        set_active_layer_axes_labels(
            self._napari_viewer, tuple(setting_labels)
        )  # type: ignore
        self._selected_layer = None


@_metadata_component
class AxisTranslations:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'AxisMetadata'

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _translation_spinbox_tuple: tuple[QDoubleSpinBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: 'Layer | None'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._component_name = 'AxisTranslates'
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel('Translate:')
        component_qlabel.setStyleSheet('font-weight: bold')
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._translation_spinbox_tuple: tuple[QDoubleSpinBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_translates = get_axes_translations(
            self._napari_viewer, active_layer
        )  # type: ignore
        for i in range(len(layer_translates)):
            with QSignalBlocker(self._translation_spinbox_tuple[i]):
                self._translation_spinbox_tuple[i].setValue(
                    layer_translates[i]
                )

    def get_entries_dict(
        self, layout_mode: str
    ) -> dict[
        int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
    ]:
        returning_dict: dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                self._axis_name_labels_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['translate_spinbox'] = (
                self._translation_spinbox_tuple[i],
                1,
                1,
                '_on_axis_translate_spin_box_adjusted',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                self._inherit_checkbox_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        (
            self._axis_name_labels_tuple,
            self._translation_spinbox_tuple,
            self._inherit_checkbox_tuple,
        ) = _reset_widget_tuples(
            cast(tuple[QWidget, ...], self._axis_name_labels_tuple),
            cast(tuple[QWidget, ...], self._translation_spinbox_tuple),
            cast(tuple[QWidget, ...], self._inherit_checkbox_tuple),
        )

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = _get_axis_label_tuple(
            self._napari_viewer, layer
        )  # type: ignore
        setting_translation_tuple: tuple[QDoubleSpinBox, ...] = (
            _get_double_spinbox_tuple(
                self._napari_viewer,
                layer,
                'get_axes_translations',
                (-1000000.0, 1000000.0),
                1,
                1.0,
                'none',
            )
        )  # type: ignore
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        self._axis_name_labels_tuple = setting_name_tuple
        self._translation_spinbox_tuple = setting_translation_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        main_widget: MetadataWidget = self._main_widget  # type: ignore
        main_widget.connect_axis_components(self)  # type: ignore

    def set_line_edit_labels(self, axes_tuples: tuple[str, ...]) -> None:
        if len(self._axis_name_labels_tuple) != len(axes_tuples):
            show_info('Number of axes does not match number of labels')
        for i in range(len(self._axis_name_labels_tuple)):
            if self._axis_name_labels_tuple[i].text() != axes_tuples[i]:
                if axes_tuples[i] == '':
                    self._axis_name_labels_tuple[i].setText(f'{i}')
                    continue
                self._axis_name_labels_tuple[i].setText(axes_tuples[i])

    def get_spin_box_values(self) -> tuple[float, ...]:
        return tuple(
            self._translation_spinbox_tuple[i].value()
            for i in range(len(self._translation_spinbox_tuple))
        )

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = get_active_layer(self._napari_viewer)
        if current_layer is None:
            return
        current_layer_translates: tuple[float, ...] = get_axes_translations(
            self._napari_viewer, current_layer
        )  # type: ignore
        template_translates: tuple[float, ...] = get_axes_translations(
            self._napari_viewer, template_layer
        )  # type: ignore
        setting_translates: list[float] = []
        checkbox_list: tuple[QCheckBox, ...] = self._inherit_checkbox_tuple
        for i in range(len(checkbox_list)):
            if checkbox_list[i].isChecked():
                setting_translates.append(template_translates[i])
            else:
                setting_translates.append(current_layer_translates[i])
        set_active_layer_axes_translations(
            self._napari_viewer, tuple(setting_translates)
        )  # type: ignore
        self._selected_layer = None


@_metadata_component
class AxisScales:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'AxisMetadata'

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _scale_spinbox_tuple: tuple[QDoubleSpinBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: 'Layer | None'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._component_name = 'AxisScales'
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel('Scale:')
        component_qlabel.setStyleSheet('font-weight: bold')
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._scale_spinbox_tuple: tuple[QDoubleSpinBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_scales = get_axes_scales(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_scales)):
            with QSignalBlocker(self._scale_spinbox_tuple[i]):
                self._scale_spinbox_tuple[i].setValue(layer_scales[i])

    def get_entries_dict(
        self, layout_mode: str
    ) -> dict[
        int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
    ]:
        returning_dict: dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                self._axis_name_labels_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['scale_spinbox'] = (
                self._scale_spinbox_tuple[i],
                1,
                1,
                '_on_axis_scale_spin_box_adjusted',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                self._inherit_checkbox_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        (
            self._axis_name_labels_tuple,
            self._scale_spinbox_tuple,
            self._inherit_checkbox_tuple,
        ) = _reset_widget_tuples(
            cast(tuple[QWidget, ...], self._axis_name_labels_tuple),
            cast(tuple[QWidget, ...], self._scale_spinbox_tuple),
            cast(tuple[QWidget, ...], self._inherit_checkbox_tuple),
        )

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = _get_axis_label_tuple(
            self._napari_viewer, layer
        )  # type: ignore
        setting_scale_tuple: tuple[QDoubleSpinBox, ...] = (
            _get_double_spinbox_tuple(
                self._napari_viewer,
                layer,
                'get_axes_scales',
                (0, 1000000.0),
                3,
                0.1,
                'none',
            )
        )  # type: ignore
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        self._axis_name_labels_tuple = setting_name_tuple
        self._scale_spinbox_tuple = setting_scale_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        main_widget: MetadataWidget = self._main_widget  # type: ignore
        main_widget.connect_axis_components(self)  # type: ignore

    def set_line_edit_labels(self, axes_tuples: tuple[str, ...]) -> None:
        if len(self._axis_name_labels_tuple) != len(axes_tuples):
            show_info('Number of axes does not match number of labels')
        for i in range(len(self._axis_name_labels_tuple)):
            if self._axis_name_labels_tuple[i].text() != axes_tuples[i]:
                if axes_tuples[i] == '':
                    self._axis_name_labels_tuple[i].setText(f'{i}')
                    continue
                self._axis_name_labels_tuple[i].setText(axes_tuples[i])

    def get_spin_box_values(self) -> tuple[float, ...]:
        return tuple(
            self._scale_spinbox_tuple[i].value()
            for i in range(len(self._scale_spinbox_tuple))
        )

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = get_active_layer(self._napari_viewer)
        if current_layer is None:
            return
        current_layer_scales: tuple[float, ...] = get_axes_scales(
            self._napari_viewer, current_layer
        )  # type: ignore
        template_scales: tuple[float, ...] = get_axes_scales(
            self._napari_viewer, template_layer
        )  # type: ignore
        setting_scales: list[float] = []
        checkbox_list: tuple[QCheckBox, ...] = self._inherit_checkbox_tuple
        for i in range(len(checkbox_list)):
            if checkbox_list[i].isChecked():
                setting_scales.append(template_scales[i])
            else:
                setting_scales.append(current_layer_scales[i])
        set_active_layer_axes_scales(
            self._napari_viewer, tuple(setting_scales)
        )  # type: ignore
        self._selected_layer = None


@_metadata_component
class AxisUnits:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = 'AxisMetadata'

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _type_combobox_tuple: tuple[QComboBox, ...]
    _unit_combobox_tuple: tuple[QComboBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: 'Layer | None'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._component_name = 'AxisUnits'
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel('Units:')
        component_qlabel.setStyleSheet('font-weight: bold')
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._type_combobox_tuple: tuple[QComboBox, ...] = ()
        self._unit_combobox_tuple: tuple[QComboBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_units = get_axes_units(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_units)):
            with QSignalBlocker(self._unit_combobox_tuple[i]):
                # remove all items from the combobox
                self._unit_combobox_tuple[i].clear()
                if str(layer_units[i]) in SpaceUnits.names():
                    self._unit_combobox_tuple[i].addItems(SpaceUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(
                        self._unit_combobox_tuple[i].findText(
                            str(layer_units[i])
                        )
                    )
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(
                            self._type_combobox_tuple[i].findText('space')
                        )
                elif str(layer_units[i]) in TimeUnits.names():
                    self._unit_combobox_tuple[i].addItems(TimeUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(
                        self._unit_combobox_tuple[i].findText(
                            str(layer_units[i])
                        )
                    )
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(
                            self._type_combobox_tuple[i].findText('time')
                        )
                else:
                    self._unit_combobox_tuple[i].addItems(SpaceUnits.names())
                    self._unit_combobox_tuple[i].addItems(TimeUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(
                        self._unit_combobox_tuple[i].findText('pixel')
                    )
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(
                            self._type_combobox_tuple[i].findText('string')
                        )

    def get_entries_dict(
        self, layout_mode: str
    ) -> dict[
        int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
    ]:
        returning_dict: dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                self._axis_name_labels_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['type_combobox'] = (
                self._type_combobox_tuple[i],
                1,
                1,
                '_on_type_combobox_changed',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['unit_combobox'] = (
                self._unit_combobox_tuple[i],
                1,
                1,
                '_on_unit_combobox_changed',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                self._inherit_checkbox_tuple[i],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        (
            self._axis_name_labels_tuple,
            self._type_combobox_tuple,
            self._unit_combobox_tuple,
            self._inherit_checkbox_tuple,
        ) = _reset_widget_tuples(
            self._axis_name_labels_tuple,
            self._type_combobox_tuple,
            self._unit_combobox_tuple,
            self._inherit_checkbox_tuple,
        )

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = _get_axis_label_tuple(
            self._napari_viewer, layer
        )  # type: ignore
        setting_type_combobox_tuple: tuple[QComboBox, ...] = ()
        setting_unit_combobox_tuple: tuple[QComboBox, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        layer_units: tuple[pint.Unit, ...] = get_axes_units(
            self._napari_viewer, layer
        )  # type: ignore
        for i in range(layer_dimensions):
            setting_unit_string: str = str(layer_units[i])
            setting_type_combobox: QComboBox = QComboBox()
            setting_type_combobox.addItems(AxisType.names())
            setting_unit_combobox: QComboBox = QComboBox()
            if setting_unit_string in SpaceUnits.names():
                setting_unit_combobox.addItems(SpaceUnits.names())
                setting_unit_combobox.setCurrentIndex(
                    setting_unit_combobox.findText(setting_unit_string)
                )
                setting_type_combobox.setCurrentIndex(
                    setting_type_combobox.findText('space')
                )
            elif setting_unit_string in TimeUnits.names():
                setting_unit_combobox.addItems(TimeUnits.names())
                setting_unit_combobox.setCurrentIndex(
                    setting_unit_combobox.findText(setting_unit_string)
                )
                setting_type_combobox.setCurrentIndex(
                    setting_type_combobox.findText('time')
                )
            else:
                setting_unit_combobox.addItems(TimeUnits.names())
                setting_unit_combobox.addItems(SpaceUnits.names())
                setting_unit_combobox.setCurrentIndex(
                    setting_unit_combobox.findText('none')
                )
                setting_type_combobox.setCurrentIndex(
                    setting_type_combobox.findText('string')
                )
            setting_type_combobox_tuple += (setting_type_combobox,)
            setting_unit_combobox_tuple += (setting_unit_combobox,)
        self._axis_name_labels_tuple = setting_name_tuple
        self._type_combobox_tuple = setting_type_combobox_tuple
        self._unit_combobox_tuple = setting_unit_combobox_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        main_widget: MetadataWidget = self._main_widget  # type: ignore
        main_widget.connect_axis_components(self)  # type: ignore

    def set_line_edit_labels(self, axes_tuples: tuple[str, ...]) -> None:
        if len(self._axis_name_labels_tuple) != len(axes_tuples):
            show_info('Number of axes does not match number of labels')
        for i in range(len(self._axis_name_labels_tuple)):
            if self._axis_name_labels_tuple[i].text() != axes_tuples[i]:
                if axes_tuples[i] == '':
                    self._axis_name_labels_tuple[i].setText(f'{i}')
                    continue
                self._axis_name_labels_tuple[i].setText(axes_tuples[i])

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = get_active_layer(self._napari_viewer)
        if current_layer is None:
            return
        current_layer_units: tuple[float, ...] = get_axes_units(
            self._napari_viewer, current_layer
        )  # type: ignore
        template_units: tuple[float, ...] = get_axes_units(
            self._napari_viewer, template_layer
        )  # type: ignore
        setting_units: list[float] = []
        checkbox_list: tuple[QCheckBox, ...] = self._inherit_checkbox_tuple
        for i in range(len(checkbox_list)):
            if checkbox_list[i].isChecked():
                setting_units.append(template_units[i])
            else:
                setting_units.append(current_layer_units[i])
        set_active_layer_axes_units(self._napari_viewer, tuple(setting_units))  # type: ignore
        self._selected_layer = None


def _reset_widget_tuples(*args: tuple[QWidget, ...]):
    for tuple_of_widgets in args:
        for widget in tuple_of_widgets:
            widget.setParent(None)
            widget.deleteLater()
    return tuple(() for _ in range(len(args)))


def _get_axis_label_tuple(
    viewer: 'ViewerModel', layer: 'Layer | None'
) -> tuple[QLabel, ...]:
    if layer is None:
        return ()
    axis_labels_tuple = get_axes_labels(viewer, layer)
    returning_tuple: tuple[QLabel, ...] = ()
    for label_index, label in enumerate(axis_labels_tuple):
        axis_label = QLabel()
        axis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        axis_label.setText(label)
        if label == '':
            axis_label.setText(f'{label_index}')
        returning_tuple += (axis_label,)
    return returning_tuple


def _get_double_spinbox_tuple(
    viewer: 'ViewerModel',
    layer: 'Layer | None',
    obtain_tuple_method_str: str,
    spinbox_range: tuple[float, float],
    spinbox_decimals: int,
    spinbox_single_step: float,
    adaptive_type: str = 'none',
) -> tuple[QDoubleSpinBox, ...]:
    if layer is None:
        return ()
    setting_values: tuple[float, ...]
    try:
        setting_values = globals()[obtain_tuple_method_str](viewer, layer)
    except KeyError as err:
        raise KeyError(
            f'Method {obtain_tuple_method_str} is not a valid method for AxisScales'
        ) from err
    returning_tuple: tuple[QDoubleSpinBox, ...] = ()
    for i in range(len(setting_values)):
        spinbox: QDoubleSpinBox = QDoubleSpinBox()
        spinbox.setDecimals(spinbox_decimals)
        spinbox.setSingleStep(spinbox_single_step)
        spinbox.setMaximum(spinbox_range[1])
        spinbox.setMinimum(spinbox_range[0])
        spinbox.setValue(setting_values[i])
        if adaptive_type == 'adaptive':
            spinbox.setStepType(
                QAbstractSpinBox.StepType.AdaptiveDecimalStepType
            )
        returning_tuple += (spinbox,)
    return returning_tuple


def _get_checkbox_tuple(layer: 'Layer | None') -> tuple[QCheckBox, ...]:
    if layer is None:
        return ()
    returning_tuple: tuple[QCheckBox, ...] = ()
    for _ in range(layer.ndim):
        inherit_checkbox: QCheckBox = QCheckBox(INHERIT_STRING)
        inherit_checkbox.setChecked(True)
        inherit_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        returning_tuple += (inherit_checkbox,)
    return returning_tuple


""" This is the class that integrates all of the axis metadata components together and instantiates them. This class itself
is instantiated in the MetadataWidget class, which is ultimately the main class passed to napari. This class will only hold the
components instances and everything else is handled in the MetadataWidget class or the individual metadata component classes."""


class AxisMetadata:
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _axis_metadata_components_dict: dict[str, MetadataComponent]

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        self._axis_metadata_components_dict: dict[str, MetadataComponent] = {}

        for (
            metadata_comp_name,
            metadata_component_class,
        ) in METADATA_COMPONENTS_DICT.items():
            if metadata_component_class.SUBMENU == 'AxisMetadata':
                self._axis_metadata_components_dict[metadata_comp_name] = (
                    metadata_component_class(napari_viewer, main_widget)
                )


class AxesInheritance:
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget

    _inheritance_layer_label: QLabel
    _layer_name_scroll_area: QScrollArea

    inheritance_layer: 'Layer | None'

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget | None = None
    ):
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        self.inheritance_layer = None

        self.inheritance_layer = None

        self._inheritance_layer_label = QLabel('Inheriting from layer')
        self._inheritance_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._inheritance_layer_label.setStyleSheet('font-weight: bold;')
        self._inheritance_layer_name = QLabel('None selected')
        self._inheritance_layer_name.setWordWrap(False)

        label_container = QWidget()
        label_layout = QHBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(self._inheritance_layer_name)
        label_layout.addStretch(1)

        self._layer_name_scroll_area = QScrollArea()
        self._layer_name_scroll_area.setWidgetResizable(True)
        self._layer_name_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._layer_name_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._layer_name_scroll_area.setFrameShape(QFrame.NoFrame)  # type: ignore
        self._layer_name_scroll_area.setWidget(label_container)

        set_layer_button: QPushButton = QPushButton('Set current layer')
        set_layer_button.clicked.connect(
            self._set_current_layer_to_inheritance
        )
        self._inheritance_select_layer_button = set_layer_button

        apply_inheritance_button: QPushButton = QPushButton('Apply')
        apply_inheritance_button.clicked.connect(self._apply_inheritance)
        self._inheritance_apply_button = apply_inheritance_button

    def _set_current_layer_to_inheritance(self) -> None:
        current_layer = get_active_layer(self._napari_viewer)  # type: ignore
        if current_layer == self.inheritance_layer:
            return
        if current_layer is None:
            self._inheritance_layer_name.setText('None selected')
        else:
            layer_name = current_layer.name
            self._inheritance_layer_name.setText(layer_name)
            self.inheritance_layer = current_layer

    def _apply_inheritance(self) -> None:
        if self.inheritance_layer is None:
            return
        self._main_widget.apply_inheritance_to_current_layer(
            self.inheritance_layer
        )  # type: ignore


class InheritanceWidget(QWidget):
    def __init__(
        self, napari_viewer: 'ViewerModel', parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._napari_viewer = napari_viewer

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        )

        self._inheritance_layer_label = QLabel('Inheriting from layer')
        self._inheritance_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._inheritance_layer_label.setStyleSheet('font-weight: bold;')
        self._inheritance_layer_name = QLabel('None selected')
        self._inheritance_layer_name.setWordWrap(False)

        label_container = QWidget()
        label_layout = QHBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(self._inheritance_layer_name)
        label_layout.addStretch(1)

        self._layer_name_scroll_area = QScrollArea()
        self._layer_name_scroll_area.setWidgetResizable(True)
        self._layer_name_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._layer_name_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._layer_name_scroll_area.setFrameShape(QFrame.NoFrame)  # type: ignore
        self._layer_name_scroll_area.setWidget(label_container)

        self._inheritance_select_layer_button = QPushButton(
            'Set current layer'
        )
        self._inheritance_apply_button = QPushButton('Apply')

        self._layout.addWidget(self._inheritance_layer_label)
        self._layout.addWidget(self._layer_name_scroll_area)
        self._layout.addWidget(self._inheritance_select_layer_button)
        self._layout.addWidget(self._inheritance_apply_button)
        self._layout.addStretch(1)


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

        self._inheritance_instance = AxesInheritance(napari_viewer, self)

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

        self._collapsible_vertical_file_metadata: VerticalSectionContainer = (
            VerticalSectionContainer(self._napari_viewer)
        )
        self._collapsible_vertical_file_metadata._set_button_text(
            'File metadata'
        )
        self._collapsible_vertical_file_metadata._set_expanding_area_widget(
            self._vert_file_general_metadata_container
        )

        self._collapsible_vertical_editable_metadata: VerticalSectionContainer = VerticalSectionContainer(
            self._napari_viewer
        )
        self._collapsible_vertical_editable_metadata._set_button_text(
            'Axes metadata'
        )
        self._collapsible_vertical_editable_metadata._set_expanding_area_widget(
            self._vert_axis_metadata_container
        )

        self._collapsible_vertical_inheritance: VerticalSectionContainer = (
            VerticalSectionContainer(self._napari_viewer)
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

        horizontal_container: QScrollArea = QScrollArea()
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

        self._collapsible_horizontal_file_metadata: HorizontalSectionContainer = HorizontalSectionContainer(
            self._napari_viewer
        )
        self._collapsible_horizontal_file_metadata._set_button_text(
            'File metadata'
        )
        self._collapsible_horizontal_file_metadata._set_expanding_area_widget(
            self._hori_file_general_metadata_container
        )

        self._collapsible_horizontal_editable_metadata: HorizontalSectionContainer = HorizontalSectionContainer(
            self._napari_viewer
        )
        self._collapsible_horizontal_editable_metadata._set_button_text(
            'Axes metadata'
        )
        self._collapsible_horizontal_editable_metadata._set_expanding_area_widget(
            self._hori_axis_metadata_container
        )

        self._collapsible_horizontal_inheritance: HorizontalSectionContainer = HorizontalSectionContainer(
            self._napari_viewer
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
                axis_component: MetadataComponent = components_dict[name]  # type: ignore

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
                        tuple[QWidget, int, int, str, Qt.AlignmentFlag | None],
                    ],
                ] = axis_component.get_entries_dict(orientation)  # type: ignore

                for axis_index in entries_dict:
                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[
                        str,
                        tuple[QWidget, int, int, str, Qt.AlignmentFlag | None],
                    ] = entries_dict[axis_index]  # type: ignore

                    sum_of_column_spans: int = 0

                    for widget_name in axis_entries_dict:
                        entry_widget: QWidget = axis_entries_dict[widget_name][
                            0
                        ]
                        entry_widget.setSizePolicy(
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding,
                        )
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[
                            widget_name
                        ][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft
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
                axis_component: MetadataComponent = components_dict[name]  # type: ignore

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
                        tuple[QWidget, int, int, str, Qt.AlignmentFlag | None],
                    ],
                ] = axis_component.get_entries_dict(orientation)  # type: ignore

                max_axis_col_spans: int = 0

                for axis_index in entries_dict:
                    current_axis_col_sum: int = 0

                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[
                        str,
                        tuple[QWidget, int, int, str, Qt.AlignmentFlag | None],
                    ] = entries_dict[axis_index]  # type: ignore

                    for widget_name in axis_entries_dict:
                        entry_widget: QWidget = axis_entries_dict[widget_name][
                            0
                        ]
                        entry_widget.setSizePolicy(
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding,
                        )
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[
                            widget_name
                        ][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft

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

        inheritance_instance: AxesInheritance = self._inheritance_instance

        setting_layout: QGridLayout | None = None

        if orientation == 'vertical':
            self._reset_layout(vert_inheritance_layout)
            setting_layout = vert_inheritance_layout
        else:
            self._reset_layout(hori_inheritance_layout)
            setting_layout = hori_inheritance_layout

        setting_layout.addWidget(inheritance_instance._inheritance_layer_label)
        setting_layout.addWidget(inheritance_instance._layer_name_scroll_area)
        setting_layout.addWidget(
            inheritance_instance._inheritance_select_layer_button
        )
        setting_layout.addWidget(
            inheritance_instance._inheritance_apply_button
        )

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

    def _on_name_line_changed(self, text: str) -> None:
        sender_line_edit: QLineEdit = cast(QLineEdit, self.sender())
        active_layer: Layer | None = get_active_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            sender_line_edit.setText('No layer selected')
            return
        if text == active_layer.name:
            return
        active_layer.name = text

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
        set_active_layer_axes_labels(self._viewer, axes_tuples)  # type: ignore
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
        set_active_layer_axes_translations(self._viewer, axes_tuples)  # type: ignore

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
            set_active_layer_axes_scales(self._viewer, axis_scales_list)  # type: ignore
            return
        set_active_layer_axes_scales(self._viewer, axes_tuples)  # type: ignore

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
        unit_registry: pint.UnitRegistry = current_units[0]._REGISTRY  # type: ignore
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

        setting_units_list: list[pint.Unit | str] = []
        for axis_number in range(len(unit_combobox_tuple)):
            unit_string: str = unit_combobox_tuple[axis_number].currentText()  # type: ignore
            unit_pint: pint.Unit
            if unit_string == 'none':
                unit_pint: pint.Unit = unit_registry('').units
            else:
                unit_pint = unit_registry(unit_string).units  # type: ignore
            setting_units_list.append(unit_pint)
        set_active_layer_axes_units(self._napari_viewer, setting_units_list)  # type: ignore

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
        unit_registry: pint.UnitRegistry = current_units[0]._REGISTRY  # type: ignore
        setting_units_list: list[pint.Unit | str] = []
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
            unit_pint: pint.Unit
            if unit_string == 'none':
                unit_pint: pint.Unit = unit_registry('').units
            else:
                unit_pint = unit_registry(unit_string).units  # type: ignore
            setting_units_list.append(unit_pint)
        set_active_layer_axes_units(self._napari_viewer, setting_units_list)  # type: ignore

    def apply_inheritance_to_current_layer(
        self, template_layer: 'Layer'
    ) -> None:
        active_layer = get_active_layer(self._napari_viewer)
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
