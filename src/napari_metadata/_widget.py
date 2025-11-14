import pint

from copy import deepcopy
from typing import TYPE_CHECKING, Optional, Sequence, cast, Tuple, List, Protocol, ClassVar

from qtpy.QtCore import Qt, QObject, QRect, QSignalBlocker, QSize
from qtpy.QtGui import QShowEvent, QPainter, QFontMetrics
from qtpy.QtWidgets import (
    QComboBox,
    QSizePolicy,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QDockWidget,
    QMainWindow,
    QStyle,
    QStyleOptionButton,
    QLayout,
    QStackedLayout,
    QCheckBox, 
    QDoubleSpinBox,
    QLayoutItem, 
    QTextEdit,
    QSpacerItem
)

from napari_metadata._model import (
    coerce_extra_metadata,
    is_metadata_equal_to_original,
    get_active_layer,
    get_layer_data_shape,
    get_layer_data_dtype,
    get_layer_source_path,
    get_layer_dimensions,
    get_axes_labels,
    set_active_layer_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    set_active_layer_axes_units,
    set_active_layer_axes_scales,
    set_active_layer_axes_translations,
)
from napari_metadata._space_units import SpaceUnits
from napari_metadata._time_units import TimeUnits

from napari_metadata._file_size import generate_display_size
from napari_metadata._axis_type import AxisType

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer
    from napari.utils.notifications import show_info

INHERIT_STRING = "Inherit"

"""This protocol is made to store the general metadata components that are not the axis components. They differn from the axis components
because they only get one widget per entry and I didn't wanto to complicate (complicate more) the extension patterns so it'll have to stay like this.
It might be best if the plugin won't allow the user to modify any of these except for the layer name.
NOTE: It is 100% possible to integrate them into a single type of component by passing lists instead of single values in the get_entries_dict but It might get too complex to extend?"""
class MetadataComponent(Protocol):
    _component_name: str
    _napari_viewer: "ViewerModel"
    _component_qlabel: QLabel
    SUBMENU: str

    """All general metadata components should pass the napari viewer and the main widget (This is the MetaDataWidget that isn't declared until later... SOMEBODY
    SHOULD MAKE A PROTOCOL FOR THIS....). This is to make sure that the components can call methods from the MetaDataWidget in case they need to interact between components."""
    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None: ...
    
    """I am suggesting the load_entries method to update/load anything that the component needs to display the information."""
    def load_entries(self, layer: "Layer | None" = None) -> None: ...

    """ This method returns the dictionary that will be used to populate the general metadata QGridLayout.
    It requires you to input the type of layout, either horizontal or vertical, with vertical set to default. 
    It should return a dictionary with the name of the entries as keys (They'll be set in bold capital letters) and a tuple with the corresponding
    QWidget, the row span, the column span, the calling method as a string or none if there's no method """
    def get_entries_dict(self, layout_mode: str) ->  dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] | dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]]: ...

    """ This method returns a boolean that will determine if the entry is to the left or below the name of the entry. """
    def get_under_label(self, layout_mode: str) -> bool: ...

METADATA_COMPONENTS_DICT: dict[str, type[MetadataComponent]] = {}

""" This decorator is used to register the MetadataComponent class in the METADATA_COMPONENTS_DICT dictionary."""
def _metadata_component(_setting_class: type[MetadataComponent]) -> type[MetadataComponent]:
    METADATA_COMPONENTS_DICT[_setting_class.__name__] = _setting_class
    return _setting_class

@_metadata_component
class LayerNameComponent():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "GeneralMetadata"

    _layer_name_line_edit: QLineEdit

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        
        component_qlabel: QLabel = QLabel("Layer Name:")
        component_qlabel.setStyleSheet("font-weight: bold;") # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        
        layer_name_line_edit = QLineEdit()
        self._layer_name_line_edit = layer_name_line_edit
        layer_name_line_edit.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self._component_name = "LayerName"

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._layer_name_line_edit.setText("None selected") # type: ignore
            return
        self._layer_name_line_edit.setText(active_layer.name) # type: ignore

    def get_entries_dict(self, layout_mode: str = "vertical") -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = {}
        if layout_mode == "vertical":
            returning_dict["LayerName"] = (self._layer_name_line_edit, 1, 2, "_on_name_line_changed", Qt.AlignmentFlag.AlignTop) # type: ignore
        else:
            returning_dict["LayerName"] = (self._layer_name_line_edit, 1, 3, "_on_name_line_changed", Qt.AlignmentFlag.AlignTop) # type: ignore
        return returning_dict 

    def get_under_label(self, layout_mode: str = "vertical") -> bool:
        if layout_mode == "vertical":
            return True
        else:
            return False

@_metadata_component
class LayerShapeComponent():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "GeneralMetadata"

    _layer_shape_label: QLabel

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel("Layer Shape:")
        component_qlabel.setStyleSheet("font-weight: bold;") # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel 


        shape_label: QLabel = QLabel("None selected")
        shape_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_shape_label = shape_label
        
        self._component_name = "LayerShape"

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._layer_shape_label.setText("None selected") # type: ignore
            return
        self._layer_shape_label.setText(str(get_layer_data_shape(active_layer))) # type: ignore

    def get_entries_dict(self, layout_mode: str = "vertical") -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = {}
        if layout_mode == "vertical":
            returning_dict["LayerShape"] = (self._layer_shape_label, 1, 1, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        else:
            returning_dict["LayerShape"] = (self._layer_shape_label, 1, 2, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = "vertical") -> bool:
        return False

@_metadata_component
class LayerDataTypeComponent():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "GeneralMetadata"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel("Layer DataType:")
        component_qlabel.setStyleSheet("font-weight: bold;") # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel 

        data_type_label: QLabel = QLabel("None selected")
        data_type_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_data_type_label = data_type_label

        self._component_name = "LayerDataType"

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._layer_data_type_label.setText("None selected") # type: ignore
            return
        self._layer_data_type_label.setText(str(get_layer_data_dtype(active_layer))) # type: ignore

    def get_entries_dict(self, layout_mode: str = "vertical") -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = {}
        if layout_mode == "vertical":
            returning_dict["LayerDataType"] = (self._layer_data_type_label, 1, 1, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        else:
            returning_dict["LayerDataType"] = (self._layer_data_type_label, 1, 2, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = "vertical") -> bool:
        return False

@_metadata_component
class LayerFileSizeComponent():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "GeneralMetadata"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel("File Size:")
        component_qlabel.setStyleSheet("font-weight: bold;") # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel 

        file_size_label: QLabel = QLabel("None selected")
        file_size_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layer_file_size_label = file_size_label

        self._component_name = "LayerFileSize"

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._layer_file_size_label.setText("None selected") # type: ignore
            return
        self._layer_file_size_label.setText(str(generate_display_size(active_layer))) # type: ignore

    def get_entries_dict(self, layout_mode: str = "vertical") -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = {}
        if layout_mode == "vertical":
            returning_dict["LayerFileSize"] = (self._layer_file_size_label, 1, 1, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        else:
            returning_dict["LayerFileSize"] = (self._layer_file_size_label, 1, 2, "", Qt.AlignmentFlag.AlignLeft) # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = "vertical") -> bool:
        return False

@_metadata_component
class SourcePathComponent():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "GeneralMetadata"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._component_name = "SourcePath"
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget

        component_qlabel: QLabel = QLabel("Source Path:")
        component_qlabel.setStyleSheet("font-weight: bold;") # type: ignore
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel 

        source_path_text_edit: SingleLineTextEdit = SingleLineTextEdit()
        source_path_text_edit.setPlainText("None selected")
        source_path_text_edit.setReadOnly(True)
        source_path_text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        source_path_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._source_path_text_edit = source_path_text_edit

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._source_path_text_edit.setPlainText("None selected") # type: ignore
            font_metrics = QFontMetrics(self._source_path_text_edit.font())
            self._source_path_text_edit.setMaximumHeight(font_metrics.height() + 30)
            return
        self._source_path_text_edit.setPlainText(str(get_layer_source_path(active_layer))) # type: ignore
        font_metrics = QFontMetrics(self._source_path_text_edit.font())
        self._source_path_text_edit.setMaximumHeight(font_metrics.height() + 30)

    def get_entries_dict(self, layout_mode: str = "vertical") -> dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]:
        returning_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = {}
        if layout_mode == "vertical":
            returning_dict["SourcePath"] = (self._source_path_text_edit, 1, 2, "", Qt.AlignmentFlag.AlignVCenter) # type: ignore
        else:
            returning_dict["SourcePath"] = (self._source_path_text_edit, 1, 3, "", Qt.AlignmentFlag.AlignTop) # type: ignore
        return returning_dict

    def get_under_label(self, layout_mode: str = "vertical") -> bool:
        if layout_mode == "vertical":
            return True
        return False

""" This is the class that integrates all of the general metadata components together and instantiates them. This class itself
is instantiated in the MetadataWidget class, which is ultimately the main class passed to napari. This class will only hold the 
components instances and everything else is handled in the MetadataWidget class or the individual metadata component classes."""
class FileGeneralMetadata():
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _file_metadata_components_dict: dict[str, MetadataComponent]

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        self._file_metadata_components_dict: dict[str, MetadataComponent] = {}

        for metadata_comp_name, metadata_component_class in METADATA_COMPONENTS_DICT.items():
            if metadata_component_class.SUBMENU == "GeneralMetadata":
                self._file_metadata_components_dict[metadata_comp_name] = metadata_component_class(napari_viewer, main_widget)

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

    def __init__(self, viewer: "ViewerModel", parent: QWidget | None = None) -> None:

        super().__init__(parent)
        self._viewer = viewer
        self._widget_parent = parent
        layout = QVBoxLayout()
        self._layout = layout
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._layout.setSpacing(5)
        self.setLayout(layout)
        self._active_listeners = False

        layer_name_label: QLabel = QLabel("Layer name:")
        layer_name_label.setStyleSheet("font-weight: bold;")
        self._layer_name_label: QLabel = layer_name_label
        self._layout.addWidget(self._layer_name_label)

        self._layer_name_QLineEdit = QLineEdit()
        self._layer_name_QLineEdit.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self._layer_name_QLineEdit.setReadOnly(False)

        self._layout.addWidget(self._layer_name_QLineEdit)

        self._layer_data_shape_label = QLabel("Data shape:")
        self._layer_data_shape_label.setStyleSheet("font-weight: bold;")
        self._layer_data_shape_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))

        self._layer_data_shape = QLabel("None selected")
        self._layer_data_shape.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        shape_container: QWidget = QWidget()
        shape_layout: QHBoxLayout = QHBoxLayout(shape_container)
        shape_layout.setContentsMargins(0, 0, 0, 0)
        shape_layout.addWidget(self._layer_data_shape_label)
        shape_layout.addWidget(self._layer_data_shape)
        shape_layout.addStretch(1)

        self._layer_data_type_label = QLabel("Data type:")
        self._layer_data_type_label.setStyleSheet("font-weight: bold;")
        self._layer_data_type_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))

        self._layer_data_type = QLabel("None selected")
        self._layer_data_type.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        type_container: QWidget = QWidget()
        type_layout: QHBoxLayout = QHBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.addWidget(self._layer_data_type_label)
        type_layout.addWidget(self._layer_data_type)
        type_layout.addStretch(1)

        self._layer_file_size = QLabel("None selected")
        self._layer_file_size.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        self._layer_file_size_label = QLabel("File size:")
        self._layer_file_size_label.setStyleSheet("font-weight: bold;")
        self._layer_file_size_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))

        size_container: QWidget = QWidget()
        size_layout: QHBoxLayout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.addWidget(self._layer_file_size_label)
        size_layout.addWidget(self._layer_file_size)
        size_layout.addStretch(1)

        self._layout.addWidget(shape_container)
        self._layout.addWidget(type_container)
        self._layout.addWidget(size_container)

        self._layer_path_label = QLabel("Source path:")
        self._layer_path_label.setStyleSheet("font-weight: bold;")
        self._layout.addWidget(self._layer_path_label)

        self._layer_path_line_edit = QLabel()
        # self._layer_path_line_edit.setReadOnly(False)
        self._layer_path_line_edit.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        paht_container = QWidget()
        path_layout = QHBoxLayout(paht_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self._layer_path_line_edit)
        
        self._layer_path_scroll_area = QScrollArea()
        self._layer_path_scroll_area.setContentsMargins(0, 0, 0, 0)
        self._layer_path_scroll_area.setMaximumHeight(45)
        self._layer_path_scroll_area.setWidgetResizable(True)
        self._layer_path_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._layer_path_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._layer_path_scroll_area.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self._layer_path_scroll_area.setFrameShape(QFrame.NoFrame) # type: ignore
        self._layer_path_scroll_area.setWidget(paht_container)
        self._layout.addWidget(self._layer_path_scroll_area)

        self._layout.addStretch(1)
        
    def _set_active_listeners(self, active_listeners: bool) -> None:
        self._active_listeners = active_listeners

    def _set_layer(self, layer: "Layer | None") -> None:
        
        if layer is None:
            self._layer_name_QLineEdit.setText("None selected")
            self._layer_path_line_edit.setText("None selected")
            self._layer_data_shape.setText("None selected")
            self._layer_data_type.setText("None selected")
            self._layer_file_size.setText("None selected")
            return

        self._layer_name_QLineEdit.setText(layer.name)
        self._layer_path_line_edit.setText(layer.source.path)
    
        data_shape: Tuple[int, ...] = get_layer_data_shape(layer)
        self._layer_data_shape.setText(f"{data_shape}")
        
        data_type: str = get_layer_data_dtype(layer)
        self._layer_data_type.setText(f"{data_type}")
        
        file_size: str = generate_display_size(layer)
        self._layer_file_size.setText(f"{file_size}")

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
    _napari_viewer: "ViewerModel"

    def __init__(self, napari_viewer: "ViewerModel") -> None: ...
    def load_entries(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None: ...
    def get_entries_dict(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]: ...
    def get_rows_and_column_spans(self) -> dict[str, int] | None: ...
    def get_checkboxes_list(self) -> list[QCheckBox]: ...

AXES_ENTRIES_DICT: dict[str, type[AxisComponent]] = {}

""" This decorator is used to register the AxisComponent class in the AXES_ENTRIES_DICT dictionary."""
def _axis_component(_setting_class: type[AxisComponent]) -> type[AxisComponent]:
    AXES_ENTRIES_DICT[_setting_class.__name__] = _setting_class
    return _setting_class

@_metadata_component
class AxisLabels():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "AxisMetadata"

    _index_labels_tuple: tuple[QLabel, ...]
    _name_line_edit_tuple: tuple[QLineEdit, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: "Layer | None"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._component_name = "AxisLabels"
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel("Labels:")
        component_qlabel.setStyleSheet("font-weight: bold")
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._index_labels_tuple = ()
        self._name_line_edit_tuple = ()
        self._inherit_checkbox_tuple = ()

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_labels = get_axes_labels(self._napari_viewer, active_layer) # type: ignore
        for i in range(len(layer_labels)):
            with QSignalBlocker(self._name_line_edit_tuple[i]):
                self._name_line_edit_tuple[i].setText(layer_labels[i])

    def get_entries_dict(self, layout_mode: str) ->  dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]]:
        returning_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = {}
        for i in range(len(self._index_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]["index_label"] = (self._index_labels_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["name_line_edit"] = (self._name_line_edit_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["inherit_checkbox"] = (self._inherit_checkbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        for i in range(len(self._index_labels_tuple)):
            self._index_labels_tuple[i].setParent(None)
            self._index_labels_tuple[i].deleteLater()  
            self._index_labels_tuple = ()
        for i in range(len(self._name_line_edit_tuple)):
            self._name_line_edit_tuple[i].setParent(None)
            self._name_line_edit_tuple[i].deleteLater()  
            self._name_line_edit_tuple = ()
        for i in range(len(self._inherit_checkbox_tuple)):
            self._inherit_checkbox_tuple[i].setParent(None)
            self._inherit_checkbox_tuple[i].deleteLater()
            self._inherit_checkbox_tuple = ()

    def _create_tuples(self, layer: "Layer | None") -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_index_tuple: tuple[QLabel, ...] = ()
        setting_name_tuple: tuple[QLineEdit, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()
        layer_labels: Tuple[str, ...] = get_axes_labels(self._napari_viewer, layer) # type: ignore
        for i in range(layer_dimensions):
            index_label: QLabel = QLabel(f"{i}")
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setting_index_tuple += (index_label,)
            name_line_edit: QLineEdit = QLineEdit()
            name_line_edit.setText(layer_labels[i])
            setting_name_tuple += (name_line_edit,)
            inherit_checkbox: QCheckBox = QCheckBox(INHERIT_STRING)
            inherit_checkbox.setChecked(True)
            setting_inherit_checkbox_tuple += (inherit_checkbox,)
        self._index_labels_tuple = setting_index_tuple
        self._name_line_edit_tuple = setting_name_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer            

    def get_rows_col_max_sums(self) -> Tuple[int, int]:
        entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = self.get_entries_dict("vertical") # type: ignore

        max_sum_cols: int = 0
        max_sum_rows: int = 0

        for axis_index in entries_dict.keys():

            current_col_sum = 0
            current_row_sum = 0

            for widget_name in entries_dict[axis_index].keys():

                current_col_sum += entries_dict[axis_index][widget_name][2]
                current_row_sum += entries_dict[axis_index][widget_name][1]

            if current_col_sum > max_sum_cols:
                max_sum_cols = current_col_sum

            if current_row_sum > max_sum_rows:
                max_sum_rows = current_row_sum

        returning_tuple = (max_sum_rows, max_sum_cols)

        return returning_tuple

@_metadata_component
class AxisTranslations():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "AxisMetadata"

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _translation_spinbox_tuple: tuple[QDoubleSpinBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: "Layer | None"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._component_name = "AxisTranslations"
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel("Translate:")
        component_qlabel.setStyleSheet("font-weight: bold")
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._translation_spinbox_tuple: tuple[QDoubleSpinBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_translates = get_axes_translations(self._napari_viewer, active_layer) # type: ignore
        for i in range(len(layer_translates)):
            with QSignalBlocker(self._translation_spinbox_tuple[i]):
                self._translation_spinbox_tuple[i].setValue(layer_translates[i])

    def get_entries_dict(self, layout_mode: str) ->  dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]]:
        returning_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]["axis_name_label"] = (self._axis_name_labels_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["translate_spinbox"] = (self._translation_spinbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["inherit_checkbox"] = (self._inherit_checkbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        for i in range(len(self._axis_name_labels_tuple)):
            self._axis_name_labels_tuple[i].setParent(None)
            self._axis_name_labels_tuple[i].deleteLater()
            self._axis_name_labels_tuple = ()
        for i in range(len(self._translation_spinbox_tuple)):
            self._translation_spinbox_tuple[i].setParent(None)
            self._translation_spinbox_tuple[i].deleteLater()
            self._translation_spinbox_tuple = ()
        for i in range(len(self._inherit_checkbox_tuple)):
            self._inherit_checkbox_tuple[i].setParent(None)
            self._inherit_checkbox_tuple[i].deleteLater()
            self._inherit_checkbox_tuple = ()

    def _create_tuples(self, layer: "Layer | None") -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = ()
        setting_translation_tuple: tuple[QDoubleSpinBox, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()
        layer_translates: Tuple[float, ...] = get_axes_translations(self._napari_viewer, layer) # type: ignore
        layer_labels: Tuple[str, ...] = get_axes_labels(self._napari_viewer, layer) # type: ignore
        for i in range(layer_dimensions):
            index_label: QLabel = QLabel(layer_labels[i])
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setting_name_tuple += (index_label,)
            translate_spin_box: QDoubleSpinBox = QDoubleSpinBox()
            translate_spin_box.setValue(layer_translates[i])
            translate_spin_box.setDecimals(3)
            translate_spin_box.setSingleStep(1.0)
            translate_spin_box.setMaximum(1000000.0)
            translate_spin_box.setMinimum(-1000000.0)
            setting_translation_tuple += (translate_spin_box,)
            inherit_checkbox: QCheckBox = QCheckBox(INHERIT_STRING)
            inherit_checkbox.setChecked(True)
            setting_inherit_checkbox_tuple += (inherit_checkbox,)
        self._axis_name_labels_tuple = setting_name_tuple
        self._translation_spinbox_tuple = setting_translation_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer
        ###### make the connection here

    def get_rows_col_max_sums(self) -> Tuple[int, int]:
        entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = self.get_entries_dict("vertical") # type: ignore

        max_sum_cols: int = 0
        max_sum_rows: int = 0

        for axis_index in entries_dict.keys():

            current_col_sum = 0
            current_row_sum = 0

            for widget_name in entries_dict[axis_index].keys():
                current_col_sum += entries_dict[axis_index][widget_name][2]
                current_row_sum += entries_dict[axis_index][widget_name][1]

            if current_col_sum > max_sum_cols:
                max_sum_cols = current_col_sum

            if current_row_sum > max_sum_rows:
                max_sum_rows = current_row_sum

        returning_tuple = (max_sum_rows, max_sum_cols)

        return returning_tuple

@_metadata_component
class AxisScales():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "AxisMetadata"

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _scale_spinbox_tuple: tuple[QDoubleSpinBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: "Layer | None"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._component_name = "AxisScales"
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel("Scale:")
        component_qlabel.setStyleSheet("font-weight: bold")
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._scale_spinbox_tuple: tuple[QDoubleSpinBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_translates = get_axes_translations(self._napari_viewer, active_layer) # type: ignore
        for i in range(len(layer_translates)):
            with QSignalBlocker(self._scale_spinbox_tuple[i]):
                self._scale_spinbox_tuple[i].setValue(layer_translates[i])

    def get_entries_dict(self, layout_mode: str) ->  dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]]:
        returning_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]["axis_name_label"] = (self._axis_name_labels_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["scale_spinbox"] = (self._scale_spinbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["inherit_checkbox"] = (self._inherit_checkbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        for i in range(len(self._axis_name_labels_tuple)):
            self._axis_name_labels_tuple[i].setParent(None)
            self._axis_name_labels_tuple[i].deleteLater()
            self._axis_name_labels_tuple = ()
        for i in range(len(self._scale_spinbox_tuple)):
            self._scale_spinbox_tuple[i].setParent(None)
            self._scale_spinbox_tuple[i].deleteLater()
            self._scale_spinbox_tuple = ()
        for i in range(len(self._inherit_checkbox_tuple)):
            self._inherit_checkbox_tuple[i].setParent(None)
            self._inherit_checkbox_tuple[i].deleteLater()
            self._inherit_checkbox_tuple = ()

    def _create_tuples(self, layer: "Layer | None") -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = ()
        setting_scale_tuple: tuple[QDoubleSpinBox, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()
        layer_scales: Tuple[float, ...] = get_axes_scales(self._napari_viewer, layer) # type: ignore
        layer_labels: Tuple[str, ...] = get_axes_labels(self._napari_viewer, layer) # type: ignore
        for i in range(layer_dimensions):
            index_label: QLabel = QLabel(layer_labels[i])
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setting_name_tuple += (index_label,)
            scale_spinbox: QDoubleSpinBox = QDoubleSpinBox()
            scale_spinbox.setValue(layer_scales[i])
            scale_spinbox.setDecimals(3)
            scale_spinbox.setSingleStep(0.01)
            scale_spinbox.setMaximum(1000000.0)
            scale_spinbox.setMinimum(-1000000.0)
            setting_scale_tuple += (scale_spinbox,)
            inherit_checkbox: QCheckBox = QCheckBox(INHERIT_STRING)
            inherit_checkbox.setChecked(True)
            setting_inherit_checkbox_tuple += (inherit_checkbox,)
        self._axis_name_labels_tuple = setting_name_tuple
        self._scale_spinbox_tuple = setting_scale_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer
        ###### make the connection here
    
    def get_rows_col_max_sums(self) -> Tuple[int, int]:
        entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = self.get_entries_dict("vertical") # type: ignore

        max_sum_cols: int = 0
        max_sum_rows: int = 0

        for axis_index in entries_dict.keys():

            current_col_sum = 0
            current_row_sum = 0

            for widget_name in entries_dict[axis_index].keys():
                current_col_sum += entries_dict[axis_index][widget_name][2]
                current_row_sum += entries_dict[axis_index][widget_name][1]

            if current_col_sum > max_sum_cols:
                max_sum_cols = current_col_sum

            if current_row_sum > max_sum_rows:
                max_sum_rows = current_row_sum

        returning_tuple = (max_sum_rows, max_sum_cols)

        return returning_tuple

@_metadata_component
class AxisUnits():
    _component_name: str
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool
    SUBMENU: str = "AxisMetadata"

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _type_combobox_tuple: tuple[QComboBox, ...]
    _unit_combobox_tuple: tuple[QComboBox, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: "Layer | None"

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._component_name = "AxisUnits"
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        component_qlabel: QLabel = QLabel("Units:")
        component_qlabel.setStyleSheet("font-weight: bold")
        component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._component_qlabel = component_qlabel
        self._under_label = False
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._type_combobox_tuple: tuple[QComboBox, ...] = ()
        self._unit_combobox_tuple: tuple[QComboBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: "Layer | None" = None) -> None:
        active_layer: "Layer | None" = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = get_active_layer(self._napari_viewer) # type: ignore
        
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_units = get_axes_units(self._napari_viewer, active_layer) # type: ignore
        for i in range(len(layer_units)):
            with QSignalBlocker(self._unit_combobox_tuple[i]):
                #remove all items from the combobox
                self._unit_combobox_tuple[i].clear()
                if str(layer_units[i]) in SpaceUnits.names():
                    self._unit_combobox_tuple[i].addItems(SpaceUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(self._unit_combobox_tuple[i].findText(str(layer_units[i])))
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(self._type_combobox_tuple[i].findText("space"))
                elif str(layer_units[i]) in TimeUnits.names():
                    self._unit_combobox_tuple[i].addItems(TimeUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(self._unit_combobox_tuple[i].findText(str(layer_units[i])))
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(self._type_combobox_tuple[i].findText("time"))
                else:
                    self._unit_combobox_tuple[i].addItems(SpaceUnits.names())
                    self._unit_combobox_tuple[i].addItems(TimeUnits.names())
                    self._unit_combobox_tuple[i].setCurrentIndex(self._unit_combobox_tuple[i].findText("pixel"))
                    with QSignalBlocker(self._type_combobox_tuple[i]):
                        self._type_combobox_tuple[i].setCurrentIndex(self._type_combobox_tuple[i].findText("string"))

    def get_entries_dict(self, layout_mode: str) ->  dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]]:
        returning_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]["axis_name_label"] = (self._axis_name_labels_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["type_combobox"] = (self._type_combobox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["unit_combobox"] = (self._unit_combobox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
            returning_dict[i]["inherit_checkbox"] = (self._inherit_checkbox_tuple[i], 1, 1, "", Qt.AlignmentFlag.AlignVCenter)
        return returning_dict

    def get_under_label(self, layout_mode: str) -> bool:
        return False

    def _reset_tuples(self) -> None:
        for i in range(len(self._axis_name_labels_tuple)):
            self._axis_name_labels_tuple[i].setParent(None)
            self._axis_name_labels_tuple[i].deleteLater()
            self._axis_name_labels_tuple = ()
        for i in range(len(self._type_combobox_tuple)):
            self._type_combobox_tuple[i].setParent(None)
            self._type_combobox_tuple[i].deleteLater()
            self._type_combobox_tuple = ()
        for i in range(len(self._unit_combobox_tuple)):
            self._unit_combobox_tuple[i].setParent(None)
            self._unit_combobox_tuple[i].deleteLater()
            self._unit_combobox_tuple = ()
        for i in range(len(self._inherit_checkbox_tuple)):
            self._inherit_checkbox_tuple[i].setParent(None)
            self._inherit_checkbox_tuple[i].deleteLater()
            self._inherit_checkbox_tuple = ()

    def _create_tuples(self, layer: "Layer | None") -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = ()
        setting_type_combobox_tuple: tuple[QDoubleSpinBox, ...] = ()
        setting_unit_combobox_tuple: tuple[QCheckBox, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()
        layer_units: Tuple[pint.Unit, ...] = get_axes_units(self._napari_viewer, layer) # type: ignore
        layer_labels: Tuple[str, ...] = get_axes_labels(self._napari_viewer, layer) # type: ignore
        for i in range(layer_dimensions):
            index_label: QLabel = QLabel(layer_labels[i])
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setting_name_tuple += (index_label,)

            setting_unit_string: str = str(layer_units[i])

            setting_type_combobox: QComboBox = QComboBox()
            setting_type_combobox.addItems(AxisType.names())
            setting_unit_combobox: QComboBox = QComboBox()
            if setting_unit_string in SpaceUnits.names():
                setting_unit_combobox.addItems(SpaceUnits.names())
                setting_unit_combobox.setCurrentIndex(setting_unit_combobox.findText(setting_unit_string))
                setting_type_combobox.setCurrentIndex(setting_type_combobox.findText("space"))
            elif setting_unit_string in TimeUnits.names():
                setting_unit_combobox.addItems(TimeUnits.names())
                setting_unit_combobox.setCurrentIndex(setting_unit_combobox.findText(setting_unit_string))
                setting_type_combobox.setCurrentIndex(setting_type_combobox.findText("time"))
            else:
                setting_unit_combobox.addItems(TimeUnits.names())
                setting_unit_combobox.addItems(SpaceUnits.names())
                setting_unit_combobox.setCurrentIndex(setting_unit_combobox.findText("pixel"))
                setting_type_combobox.setCurrentIndex(setting_type_combobox.findText("string"))
            setting_type_combobox_tuple += (setting_type_combobox,)
            setting_unit_combobox_tuple += (setting_unit_combobox,)

            inherit_checkbox: QCheckBox = QCheckBox(INHERIT_STRING)
            inherit_checkbox.setChecked(True)
            setting_inherit_checkbox_tuple += (inherit_checkbox,)
        self._axis_name_labels_tuple = setting_name_tuple
        self._type_combobox_tuple = setting_type_combobox_tuple
        self._unit_combobox_tuple = setting_unit_combobox_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer
        ###### make the connection here

    def get_rows_col_max_sums(self) -> Tuple[int, int]:
        entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = self.get_entries_dict("vertical") # type: ignore

        max_sum_cols: int = 0
        max_sum_rows: int = 0

        for axis_index in entries_dict.keys():

            current_col_sum = 0
            current_row_sum = 0

            for widget_name in entries_dict[axis_index].keys():
                current_col_sum += entries_dict[axis_index][widget_name][2]
                current_row_sum += entries_dict[axis_index][widget_name][1]

            if current_col_sum > max_sum_cols:
                max_sum_cols = current_col_sum

            if current_row_sum > max_sum_rows:
                max_sum_rows = current_row_sum

        returning_tuple = (max_sum_rows, max_sum_cols)

        return returning_tuple

""" This is the class that integrates all of the axis metadata components together and instantiates them. This class itself
is instantiated in the MetadataWidget class, which is ultimately the main class passed to napari. This class will only hold the 
components instances and everything else is handled in the MetadataWidget class or the individual metadata component classes."""
class AxisMetadata():
    _napari_viewer: "ViewerModel"
    _main_widget: QWidget
    _axis_metadata_components_dict: dict[str, MetadataComponent]

    def __init__(self, napari_viewer: "ViewerModel", main_widget: QWidget) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        self._axis_metadata_components_dict: dict[str, MetadataComponent] = {}

        for metadata_comp_name, metadata_component_class in METADATA_COMPONENTS_DICT.items():
            if metadata_component_class.SUBMENU == "AxisMetadata":
                self._axis_metadata_components_dict[metadata_comp_name] = metadata_component_class(napari_viewer, main_widget)

@_axis_component
class AxesLabels():
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: "ViewerModel"
    def __init__(self, napari_viewer: "ViewerModel") -> None:
        self._axis_component_name = "Labels"
        self._entries_dict = {}
        self._napari_viewer: "ViewerModel" = napari_viewer
        self._layout = QVBoxLayout()

    def _reset_entries(self, number_of_axes: int = 0) -> None:
        for i in range(len(self._entries_dict)):
            self._entries_dict[i]["AxisIndex"][2].deleteLater()  
            self._entries_dict[i]["AxisLabel"][2].deleteLater()  
            self._entries_dict[i]["InheritCheckBox"][2].deleteLater() 
        self._entries_dict = {}
        for i in range(number_of_axes):
            self._entries_dict[i] = {
                # Entries are: 
                # Key: [row_width, column_width, widget, calling_function_string]
                "AxisIndex":        (1, 1, QLabel(f"{i}"), None),
                "AxisLabel":        (1, 1, QLineEdit(f"{i}"), "_on_axes_label_changed"),
                "InheritCheckBox":  (1, 1, QCheckBox("Inherit"), "_on_checkbox_state_changed")
            }
            inherit_box: QCheckBox = self._entries_dict[i]["InheritCheckBox"][2]
            inherit_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            inherit_box.setChecked(True)

    def load_entries(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None:
        active_layer: "Layer | None" = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._reset_entries()
            return None
        axes_labels: Tuple[str, ...] = get_axes_labels(self._napari_viewer) # type: ignore
        self._reset_entries(len(axes_labels))
        for i, axis_label in enumerate(axes_labels):
            with QSignalBlocker(self._entries_dict[i]["AxisLabel"][2]):
                label_name_widget: QLabel = self._entries_dict[i]["AxisLabel"][2]
                label_name_widget.setText(axis_label)
        return self._entries_dict

    def _get_structure_and_calling_functions(self) -> List[Tuple[int, int, int, int, QWidget, str | None]]:
        returning_list: list[Tuple[int, int, int, int, QWidget, str | None]] = []
        if len(self._entries_dict) == 0:
            return returning_list
        for i in range(len(self._entries_dict)):
            for j, key in enumerate(self._entries_dict[i]):
                returning_list.append((i, self._entries_dict[i][key][0], j, self._entries_dict[i][key][1], self._entries_dict[i][key][2], self._entries_dict[i][key][3]))
        return returning_list

    def get_entries_dict(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]:
        if len(self._entries_dict) == 0:
            return {}
        return self._entries_dict

    def get_rows_and_column_spans(self) -> dict[str, int] | None:
        if len(self._entries_dict) == 0:
            return None
        length_of_entries = len(self._entries_dict)
        max_row = 0
        max_column = 0
        first_subdict = self._entries_dict[0]
        for key in first_subdict:
            row_span = first_subdict[key][0]
            column_span = first_subdict[key][1]
            if row_span > max_row:
                max_row = row_span
            max_column += column_span
        return {"row_span": max_row * length_of_entries, "column_span": max_column}

    def get_checkboxes_list(self) -> list[QCheckBox]:
        return [self._entries_dict[i]["InheritCheckBox"][2] for i in range(len(self._entries_dict))]

@_axis_component
class AxesTranslations():
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: "ViewerModel"
    
    def __init__(self, napari_viewer: "ViewerModel") -> None:
        self._axis_component_name = "Translate"
        self._entries_dict = {}
        self._napari_viewer: "ViewerModel" = napari_viewer

    def _reset_entries(self, number_of_axes: int = -1) -> None:
        for i in range(len(self._entries_dict)):
            self._entries_dict[i]["AxisIndex"][2].deleteLater()
            self._entries_dict[i]["AxisTranslate"][2].deleteLater()
            self._entries_dict[i]["InheritCheckBox"][2].deleteLater()
        self._entries_dict = {}
        for i in range(number_of_axes):
            self._entries_dict[i] = {
                # Entries are: 
                # Key: [row_width, column_width, widget, calling_function_string]
                "AxisIndex": (1, 1,QLabel(f"{i}"), None),
                "AxisTranslate": (1, 1, QDoubleSpinBox(), "_on_axes_translate_changed"),
                "InheritCheckBox": (1, 1, QCheckBox("Inherit"), "_on_checkbox_state_changed")
            }
            spin_box: QDoubleSpinBox = self._entries_dict[i]["AxisTranslate"][2]
            spin_box.setDecimals(2)
            spin_box.setSingleStep(1.0)
            spin_box.setValue(0.0)
            spin_box.setMinimum(-10000.0)
            spin_box.setMaximum(10000.0)
            spin_box.setKeyboardTracking(True)
            inherit_box: QCheckBox = self._entries_dict[i]["InheritCheckBox"][2]
            inherit_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            inherit_box.setChecked(True)
            

    def get_rows_and_column_spans(self) -> dict[str, int] | None:
        if len(self._entries_dict) <= 0:
            return None
        length_of_entries: int = len(self._entries_dict)
        max_row: int = -1
        max_column: int = -1
        first_subdict: dict[str, tuple[int, int, QWidget, str | None]]  = self._entries_dict[0]
        for key in first_subdict:
            row_span: int = first_subdict[key][0]
            column_span = first_subdict[key][1]
            if row_span > max_row:
                max_row = row_span
            max_column += column_span
        return {"row_span": max_row * length_of_entries, "column_span": max_column}

    def load_entries(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None:
        active_layer: "Layer | None" = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._reset_entries()
            return None
        axes_translations: Tuple[float, ...] = get_axes_translations(self._napari_viewer) # type: ignore
        self._reset_entries(len(axes_translations))
        for i, axis_translation in enumerate(axes_translations):
            spin_box: QDoubleSpinBox = self._entries_dict[i]["AxisTranslate"][2]
            spin_box.setValue(axis_translation)
        return self._entries_dict

    def _get_structure_and_calling_functions(self) -> List[Tuple[int, int, int, int, QWidget, str | None]]:
        returning_list: list[Tuple[int, int, int, int, QWidget, str | None]] = []
        if len(self._entries_dict) == -1:
            return returning_list
        for i in range(len(self._entries_dict)):
            for j, key in enumerate(self._entries_dict[i]):
                returning_list.append((i, self._entries_dict[i][key][0], j, self._entries_dict[i][key][1], self._entries_dict[i][key][2], self._entries_dict[i][key][3]))
        return returning_list

    def get_entries_dict(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]:
        return self._entries_dict

    def get_checkboxes_list(self) -> list[QCheckBox]:
        return [self._entries_dict[i]["InheritCheckBox"][2] for i in range(len(self._entries_dict))]

@_axis_component
class AxesScales():
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: "ViewerModel"
    def __init__(self, napari_viewer: "ViewerModel") -> None:
        self._axis_component_name = "Scale"
        self._entries_dict = {}
        self._napari_viewer: "ViewerModel" = napari_viewer
    
    def _reset_entries(self, number_of_axes: int = 0) -> None:
        for i in range(len(self._entries_dict)):
            self._entries_dict[i]["AxisIndex"][2].deleteLater()
            self._entries_dict[i]["AxisScale"][2].deleteLater()
            self._entries_dict[i]["InheritCheckBox"][2].deleteLater()
        self._entries_dict = {}
        for i in range(number_of_axes):
            self._entries_dict[i] = {
                "AxisIndex": (1, 1,QLabel(f"{i}"), None),
                "AxisScale": (1, 1, QDoubleSpinBox(), "_on_axes_scale_changed"),
                "InheritCheckBox": (1, 1, QCheckBox("Inherit"), "_on_checkbox_state_changed")
            }
            spin_box: QDoubleSpinBox = self._entries_dict[i]["AxisScale"][2]
            spin_box.setDecimals(3)
            spin_box.setSingleStep(0.1)
            spin_box.setValue(1.0)
            spin_box.setKeyboardTracking(True)
            spin_box.setMinimum(0.001)
            inherit_box: QCheckBox = self._entries_dict[i]["InheritCheckBox"][2]
            inherit_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            inherit_box.setChecked(True)

    def load_entries(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None:
        active_layer: "Layer | None" = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._reset_entries()
            return None
        axes_scales: Tuple[float, ...] = get_axes_scales(self._napari_viewer) # type: ignore
        self._reset_entries(len(axes_scales))
        for i, axis_scale in enumerate(axes_scales):
            spin_box: QDoubleSpinBox = self._entries_dict[i]["AxisScale"][2]
            spin_box.setValue(axis_scale)
        return self._entries_dict

    def get_entries_dict(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]:
        return self._entries_dict

    def _get_structure_and_calling_functions(self) -> List[Tuple[int, int, int, int, QWidget, str | None]]:
        returning_list: list[Tuple[int, int, int, int, QWidget, str | None]] = []
        if len(self._entries_dict) == 0:
            return returning_list
        for i in range(len(self._entries_dict)):
            for j, key in enumerate(self._entries_dict[i]):
                returning_list.append((i, self._entries_dict[i][key][0], j, self._entries_dict[i][key][1], self._entries_dict[i][key][2], self._entries_dict[i][key][3]))
        return returning_list

    def get_rows_and_column_spans(self) -> dict[str, int] | None:
        if len(self._entries_dict) == 0:
            return None
        length_of_entries = len(self._entries_dict)
        max_row = 0
        max_column = 0
        first_subdict = self._entries_dict[0]
        for key in first_subdict:
            row_span = first_subdict[key][0]
            column_span = first_subdict[key][1]
            if row_span > max_row:
                max_row = row_span
            max_column += column_span
        return {"row_span": max_row * length_of_entries, "column_span": max_column}

    def get_checkboxes_list(self) -> list[QCheckBox]:
        return [self._entries_dict[i]["InheritCheckBox"][2] for i in range(len(self._entries_dict))]

@_axis_component
class AxesUnits():
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: "ViewerModel"

    def __init__(self, napari_viewer: "ViewerModel") -> None:
        self._axis_component_name = "Units"
        self._entries_dict = {}
        self._napari_viewer: "ViewerModel" = napari_viewer

    def _reset_entries(self, number_of_axes: int = 0) -> None:
        for i in range(len(self._entries_dict)):
            self._entries_dict[i]["AxisIndex"][2].deleteLater()
            self._entries_dict[i]["AxisType"][2].deleteLater()
            self._entries_dict[i]["AxisUnit"][2].deleteLater()
            self._entries_dict[i]["InheritCheckBox"][2].deleteLater()
        self._entries_dict = {}
        for i in range(number_of_axes):
            self._entries_dict[i] = {
                "AxisIndex": (1, 1, QLabel(f"{i}"), None),
                "AxisType": (1, 1, QComboBox(), "_on_axes_type_changed"),
                "AxisUnit": (1, 1, QComboBox(), "_on_axes_unit_changed"),
                "InheritCheckBox": (1, 1, QCheckBox("Inherit"), "_on_checkbox_state_changed")
            }
            axis_type_box: QComboBox = self._entries_dict[i]["AxisType"][2]
            axis_type_box.addItems(AxisType.names())
            axis_units_box: QComboBox = self._entries_dict[i]["AxisUnit"][2]
            axis_units_box.addItems(TimeUnits.names())
            axis_units_box.addItems(SpaceUnits.names())
            inherit_box: QCheckBox = self._entries_dict[i]["InheritCheckBox"][2]
            inherit_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            inherit_box.setChecked(True)

    def load_entries(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None:
        active_layer = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            self._reset_entries()
            return None
        axes_units: Tuple[pint.Unit | str, ...] = get_axes_units(self._napari_viewer) # type: ignore
        self._reset_entries(len(axes_units))
        for i, axis_unit in enumerate(axes_units):
            with QSignalBlocker(self._entries_dict[i]["AxisUnit"][2]):
                axis_units_box: QComboBox = self._entries_dict[i]["AxisUnit"][2]
                axis_units_box.setCurrentIndex(axis_units_box.findText(str(axis_unit)))
        self._update_types()
        return self._entries_dict
    
    def _get_structure_and_calling_functions(self) -> List[Tuple[int, int, int, int, QWidget, str | None]]:
        returning_list: list[Tuple[int, int, int, int, QWidget, str | None]] = []
        if len(self._entries_dict) == 0:
            return returning_list
        for i in range(len(self._entries_dict)):
            for j, key in enumerate(self._entries_dict[i]):
                returning_list.append((i, self._entries_dict[i][key][0], j, self._entries_dict[i][key][1], self._entries_dict[i][key][2], self._entries_dict[i][key][3]))
        return returning_list

    def get_rows_and_column_spans(self) -> dict[str, int] | None:
        if len(self._entries_dict) == 0:
            return None
        length_of_entries = len(self._entries_dict)
        max_row = 0
        max_column = 0
        first_subdict = self._entries_dict[0]
        for key in first_subdict:
            row_span = first_subdict[key][0]
            column_span = first_subdict[key][1]
            if row_span > max_row:
                max_row = row_span
            max_column += column_span
        return {"row_span": max_row * length_of_entries, "column_span": max_column}

    def get_entries_dict(self) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]:
        return self._entries_dict

    def _update_types(self) -> None:
        for i in range(len(self._entries_dict)):
            axis_units_box: QComboBox = self._entries_dict[i]["AxisUnit"][2]
            current_unit_text: str = axis_units_box.currentText()
            with QSignalBlocker(self._entries_dict[i]["AxisType"][2]):
                axis_types_box: QComboBox = self._entries_dict[i]["AxisType"][2]
                if current_unit_text != "none" and TimeUnits.contains(current_unit_text):
                    axis_types_box.setCurrentIndex(axis_types_box.findText("time"))
                elif current_unit_text != "none" and SpaceUnits.contains(current_unit_text):
                    axis_types_box.setCurrentIndex(axis_types_box.findText("space"))
                elif current_unit_text != "none":
                    axis_types_box.setCurrentIndex(axis_types_box.findText("string"))
        self._update_units_lists()
    
    def _update_units_lists(self) -> None:
        for i in range(len(self._entries_dict)):
            current_unit_box: QComboBox = self._entries_dict[i]["AxisUnit"][2]
            current_unit_text: str = current_unit_box.currentText()
            with QSignalBlocker(current_unit_box):
                if current_unit_text != "none" and TimeUnits.contains(current_unit_text):
                    current_unit_box.clear()
                    current_unit_box.addItems(TimeUnits.names())
                    current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))
                elif current_unit_text != "none" and SpaceUnits.contains(current_unit_text):
                    current_unit_box.clear()
                    current_unit_box.addItems(SpaceUnits.names())
                    current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))
                elif current_unit_text != "none":
                    current_unit_box.clear()
                    current_unit_box.addItems(TimeUnits.names())
                    current_unit_box.addItems(SpaceUnits.names())
                    current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))

    def _set_types(self) -> None:
        for i in range(len(self._entries_dict)):
            current_type_box: QComboBox = self._entries_dict[i]["AxisType"][2]
            current_type_text: str = current_type_box.currentText()
            current_unit_box: QComboBox = self._entries_dict[i]["AxisUnit"][2]
            current_unit_text: str = current_unit_box.currentText()
            if current_type_text == "time":
                with QSignalBlocker(current_unit_box):
                    current_unit_box.clear()
                    current_unit_box.addItems(TimeUnits.names())
                    if current_unit_text != "none" and TimeUnits.contains(current_unit_text):
                        current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))
                    else:
                        current_unit_box.setCurrentIndex(current_unit_box.findText("second"))
            elif current_type_text == "space":
                with QSignalBlocker(current_unit_box):
                    current_unit_box.clear()
                    current_unit_box.addItems(SpaceUnits.names())
                    if current_unit_text != "none" and SpaceUnits.contains(current_unit_text):
                        current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))
                    else:
                        current_unit_box.setCurrentIndex(current_unit_box.findText("pixel"))
            elif current_type_text == "string":
                with QSignalBlocker(current_unit_box):
                    current_unit_box.clear()
                    current_unit_box.addItems(TimeUnits.names())
                    current_unit_box.addItems(SpaceUnits.names())
                    if current_unit_text != "none":
                        current_unit_box.setCurrentIndex(current_unit_box.findText(current_unit_text))
                    else:
                        try: 
                            current_unit_box.setCurrentIndex(current_unit_box.findText("pixel"))
                        except:
                            current_unit_box.setCurrentIndex(0)        

    def get_checkboxes_list(self) -> list[QCheckBox]:
        return [self._entries_dict[i]["InheritCheckBox"][2] for i in range(len(self._entries_dict))]

class EditableMetadataWidget(QWidget):
    
    _widget_parent: QWidget | None
    _current_layout: QGridLayout

    _layout: QGridLayout
    _layout_mode: str

    _active_listeners: bool

    _editable_axes_components: dict[str, AxisComponent]

    def __init__(self, viewer: "ViewerModel", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_layout = QGridLayout()
        self._viewer = viewer
        self._selected_layer = None
        self._widget_parent = parent
        layout = QGridLayout()
        self._layout = layout
        self.setLayout(layout)
        self._active_listeners = False
        self._layout_mode = "none"

        self._editable_axes_components = {
            name: cls(self._viewer) for name, cls in AXES_ENTRIES_DICT.items()
        }

#region previous code
# TODO: (Carlos Rodriguez) This is the previous code that was used for the widget but it's no longer used for it. It is still referenced in other places so I can't delete it yet

    def set_selected_layer(self, layer: Optional["Layer"]) -> None:
        if layer == self._selected_layer:
            return
        if self._selected_layer is not None:
            self._selected_layer.events.name.disconnect(
                self._on_selected_layer_name_changed
            )
            self._selected_layer.events.scale.disconnect(
                self._update_restore_enabled
            )
            self._selected_layer.events.translate.disconnect(
                self._update_restore_enabled
            )

        if layer is not None:
            self._spatial_units.set_selected_layer(layer)
            self._axes_widget.set_selected_layer(layer)
            self.name.setText(layer.name)
            layer.events.name.connect(self._on_selected_layer_name_changed)
            layer.events.scale.connect(self._update_restore_enabled)
            layer.events.translate.connect(self._update_restore_enabled)
            extras = coerce_extra_metadata(self._viewer, layer)
            time_unit = str(extras.get_time_unit())
            self._temporal_units.setCurrentText(time_unit)

        self._spacing_widget.set_selected_layer(layer)

        self._selected_layer = layer
        self._update_restore_enabled()

    def _add_attribute_row(self, name: str, widget: QWidget) -> None:
        layout = self._attribute_widget.layout()
        row = layout.rowCount()
        label = QLabel(name)
        label.setBuddy(widget)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)

    def _on_selected_layer_name_changed(self, event) -> None:
        self.name.setText(event.source.name)

    def _on_name_changed(self) -> None:
        if self._selected_layer is not None:
            self._selected_layer.name = self.name.text()
        self._update_restore_enabled()

    def _on_spatial_units_changed(self) -> None:
        unit = SpaceUnits.from_name(self._spatial_units.currentText())
        if unit is None:
            unit = SpaceUnits.NONE
        for layer in self._viewer.layers:
            extras = coerce_extra_metadata(self._viewer, layer)
            extras.set_space_unit(unit)
        self._update_restore_enabled()

    def _on_temporal_units_changed(self) -> None:
        unit = TimeUnits.from_name(self._temporal_units.currentText())
        if unit is None:
            unit = TimeUnits.NONE
        for layer in self._viewer.layers:
            extras = coerce_extra_metadata(self._viewer, layer)
            extras.set_time_unit(unit)
        self._update_restore_enabled()

    def _on_restore_clicked(self) -> None:
        assert self._selected_layer is not None
        layer = self._selected_layer
        extras = coerce_extra_metadata(self._viewer, layer)
        if original := extras.original:
            extras.axes = list(deepcopy(original.axes))
            if name := original.name:
                layer.name = name
            if scale := original.scale:
                layer.scale = scale
            if translate := original.translate:
                layer.translate = translate
            self._spatial_units.set_selected_layer(layer)
            self._axes_widget.set_selected_layer(layer)
            time_unit = str(extras.get_time_unit())
            self._temporal_units.setCurrentText(time_unit)

    def _update_restore_enabled(self) -> None:
        enabled = not is_metadata_equal_to_original(self._selected_layer)
        self._restore_defaults.setEnabled(enabled)

#endregion

    def _set_active_listeners(self, active: bool) -> None:
        self._active_listeners = active

    def _set_vertical_mode(self) -> None:
        self._layout_mode = "vertical"
        self._update_active_layer()

    def _set_horizontal_mode(self) -> None:
        self._layout_mode = "horizontal"
        self._update_active_layer()

    def _update_active_layer(self) -> None:
        if self._layout_mode != "horizontal" and self._layout_mode != "vertical":
            return
        self._reset_layout(self.layout())
        layer: "Layer | None" = get_active_layer(self._viewer)
        if layer is None:
            return
        current_row = 0
        current_column = 0
        editable_comp_name: str
        list_of_connections: List[Tuple[QWidget, str]] = []
        max_column_vert_spans: int = 0
        max_row_hori_spans: int = 0
        vert_separator_rows: List[int] = []
        hori_separator_columns: List[int] = []
        for editable_comp_class_name in self._editable_axes_components.keys():
            self._editable_axes_components[editable_comp_class_name].load_entries()
            editable_comp_name: str = self._editable_axes_components[editable_comp_class_name]._axis_component_name # type: ignore
            rows_and_column_spans: dict[str, int] | None = self._editable_axes_components[editable_comp_class_name].get_rows_and_column_spans()
            editable_comp_entries: dict[int, dict[str, tuple[int, int, QWidget, str | None]]] = self._editable_axes_components[editable_comp_class_name].get_entries_dict()
            appending_q_label = QLabel(editable_comp_name)
            appending_q_label.setStyleSheet("font-weight: bold")
            if self._layout_mode == "vertical":
                appending_q_label.setAlignment(Qt.AlignmentFlag.AlignTop)
                self._layout.addWidget(appending_q_label, current_row, 0, rows_and_column_spans["row_span"], 1)
                current_individual_widget_row = current_row
                for axis_number in editable_comp_entries:
                    current_individual_widget_column = 1
                    max_row_span = 1
                    for axis_element_name in editable_comp_entries[axis_number]:
                        adding_widget: QWidget = editable_comp_entries[axis_number][axis_element_name][2]
                        if isinstance(adding_widget, QLabel):
                            label_widget: QLabel = cast(QLabel, adding_widget)
                            label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        self._layout.addWidget(adding_widget, current_individual_widget_row, current_individual_widget_column, editable_comp_entries[axis_number][axis_element_name][0], editable_comp_entries[axis_number][axis_element_name][1])
                        callin_string = editable_comp_entries[axis_number][axis_element_name][3]
                        if callin_string is not None:
                            list_of_connections.append((adding_widget, callin_string))
                        current_individual_widget_column += editable_comp_entries[axis_number][axis_element_name][1]
                        if editable_comp_entries[axis_number][axis_element_name][0] > max_row_span:
                            max_row_span = editable_comp_entries[axis_number][axis_element_name][0]
                    current_individual_widget_row += max_row_span
                    if current_individual_widget_column > max_column_vert_spans:
                        max_column_vert_spans = current_individual_widget_column
                if editable_comp_class_name != list(self._editable_axes_components.keys())[-1]:
                    vert_separator_rows.append(current_row + rows_and_column_spans["row_span"])
                current_row += rows_and_column_spans["row_span"] + 1

            else:
                appending_q_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                appending_q_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
                self._layout.addWidget(appending_q_label, 0, current_column, 1, rows_and_column_spans["column_span"])
                
                current_individual_widget_row = 1
                
                max_axis_col_span = 0

                max_axis_row_span = 0

                for axis_number in editable_comp_entries:
                    
                    current_individual_widget_column = current_column
                    axis_element_max_row_span = 0

                    current_axis_col_span = 0
                    
                    for axis_element_name in editable_comp_entries[axis_number]:
                        
                        # if axis_element_name == "AxisIndex" and editable_comp_class_name != list(self._editable_axes_components.keys())[0]:
                        #     continue
                        adding_widget: QWidget = editable_comp_entries[axis_number][axis_element_name][2]
                        if isinstance(adding_widget, QLabel):
                            label_widget: QLabel = cast(QLabel, adding_widget)
                            label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        self._layout.addWidget(adding_widget, current_individual_widget_row, current_individual_widget_column, editable_comp_entries[axis_number][axis_element_name][0], editable_comp_entries[axis_number][axis_element_name][1])

                        current_axis_col_span += editable_comp_entries[axis_number][axis_element_name][1]

                        callin_string = editable_comp_entries[axis_number][axis_element_name][3]
                        if callin_string is not None:
                            list_of_connections.append((adding_widget, callin_string))
                        
                        if editable_comp_entries[axis_number][axis_element_name][1] > axis_element_max_row_span:
                            axis_element_max_row_span = editable_comp_entries[axis_number][axis_element_name][1]
                        current_individual_widget_column += editable_comp_entries[axis_number][axis_element_name][1]

                        if axis_element_name == list(editable_comp_entries[axis_number].keys())[-1] and current_individual_widget_column not in hori_separator_columns:
                            hori_separator_columns.append(current_individual_widget_column)

                    if current_axis_col_span > max_axis_col_span:
                        max_axis_col_span = current_axis_col_span

                    current_individual_widget_row += axis_element_max_row_span
                
                if max_axis_row_span > max_row_hori_spans:
                    max_row_hori_spans = max_axis_row_span

                current_column += max_axis_col_span + 1

        if self._layout_mode == "vertical":
            for row in vert_separator_rows:
                vert_separator = QFrame()
                vert_separator.setFrameShape(QFrame.HLine)
                vert_separator.setFrameShadow(QFrame.Sunken)
                vert_separator.setStyleSheet("background-color: grey;")
                self._layout.addWidget(vert_separator, row, 0, 1, max_column_vert_spans)

            num_of_columns: int  = self._layout.columnCount()
            for col in range(num_of_columns):
                self._layout.setColumnStretch(col, 1)
            num_of_rows: int = self._layout.rowCount()
            for row in range(num_of_rows):
                self._layout.setRowStretch(row, 1)

        else:
            hori_separator_columns = hori_separator_columns[:-1]
            for col in hori_separator_columns:
                hori_separator = QFrame()
                hori_separator.setFrameShape(QFrame.VLine)
                hori_separator.setFrameShadow(QFrame.Sunken)
                hori_separator.setStyleSheet("background-color: grey;")
                self._layout.addWidget(hori_separator, 0, col, max_row_hori_spans, 1, Qt.AlignmentFlag.AlignHCenter)
                self._layout.setColumnStretch(col, 1)

            num_of_columns: int  = self._layout.columnCount()
            for col in range(num_of_columns):
                self._layout.setColumnStretch(col, 1)
            num_of_rows: int = self._layout.rowCount()
            for row in range(num_of_rows):
                self._layout.setRowStretch(row, 1)

        self._update_widget_axes_labels()

        for widget, callin_string in list_of_connections:
            if isinstance(widget, QLineEdit):
                setting_qline_edit: QLineEdit = widget
                calling_method_string: str = callin_string
                calling_method = getattr(self, calling_method_string)
                setting_qline_edit.textEdited.connect(calling_method)
            if isinstance(widget, QComboBox):
                setting_qcombo_box: QComboBox = widget
                calling_method_string: str = callin_string
                calling_method = getattr(self, calling_method_string)
                setting_qcombo_box.currentIndexChanged.connect(calling_method)
            if isinstance(widget, QDoubleSpinBox):
                setting_qspin_box: QDoubleSpinBox = widget
                calling_method_string: str = callin_string
                calling_method = getattr(self, calling_method_string)
                setting_qspin_box.valueChanged.connect(calling_method)
            if isinstance(widget, QCheckBox):
                setting_qcheck_box: QCheckBox = widget
                calling_method_string: str = callin_string
                calling_method = getattr(self, calling_method_string)
                setting_qcheck_box.stateChanged.connect(calling_method)
    
    def _on_axes_label_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        axes_labels_instance: AxesLabels = self._editable_axes_components["AxesLabels"]
        setting_labels: Tuple[str, ...] = tuple(axes_labels_instance._entries_dict[i]["AxisLabel"][2].text() for i in range(len(axes_labels_instance._entries_dict)))
        set_active_layer_axes_labels(self._viewer, setting_labels)
        self._update_widget_axes_labels()

    def _update_widget_axes_labels(self) -> None:
        layer_labels_tuple: Tuple[str, ...] = get_axes_labels(self._viewer)
        if len(layer_labels_tuple) == 0:
            return
        for axes_component in self._editable_axes_components:
            if axes_component == "AxesLabels":
                continue
            axes_component_instance: AxisComponent = self._editable_axes_components[axes_component]
            axes_component_entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]] = axes_component_instance.get_entries_dict()
            for axis_number in axes_component_entries_dict:
                axis_index_widget: QLineEdit = axes_component_entries_dict[axis_number]["AxisIndex"][2]
                axis_index_widget.setText(layer_labels_tuple[axis_number])

    def _on_axes_unit_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        axes_units_instance: AxesUnits = self._editable_axes_components["AxesUnits"]
        setting_units_strings: list = [axes_units_instance._entries_dict[i]["AxisUnit"][2].currentText() for i in range(len(axes_units_instance._entries_dict))]
        set_active_layer_axes_units(self._viewer, tuple(setting_units_strings))
        axes_units_instance._update_types()

    def _on_axes_type_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        axes_units_instance: AxesUnits = self._editable_axes_components["AxesUnits"]
        axes_units_instance._set_types()
        axes_units_strings: list = [axes_units_instance._entries_dict[i]["AxisUnit"][2].currentText() for i in range(len(axes_units_instance._entries_dict))]
        set_active_layer_axes_units(self._viewer, tuple(axes_units_strings))

    def _on_axes_scale_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        axes_scales_instance: AxesScales = self._editable_axes_components["AxesScales"]
        setting_scales: Tuple[float, ...] = tuple(axes_scales_instance._entries_dict[i]["AxisScale"][2].value() for i in range(len(axes_scales_instance._entries_dict)))
        for current_scale in setting_scales:
            if current_scale <= 0.0:
                return
        set_active_layer_axes_scales(self._viewer, setting_scales)

    def _on_axes_translate_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        axes_translations_instance: AxesTranslations = self._editable_axes_components["AxesTranslations"]
        setting_translations: Tuple[float, ...] = tuple(axes_translations_instance._entries_dict[i]["AxisTranslate"][2].value() for i in range(len(axes_translations_instance._entries_dict)))
        set_active_layer_axes_translations(self._viewer, setting_translations)

    def _reset_layout(self, layout: "QLayout | None" = None) -> None:
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
                    item_widget.deleteLater()
        
    def _on_checkbox_state_changed(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        self.parent().parent().parent().parent()._editable_checkbox_state_changed(self._layout_mode) # type: ignore

    def _get_checkboxes_dict(self) -> dict[str, list[QCheckBox]]:
        returning_dict: dict[str, list[QCheckBox]] = {}
        for editable_comp_class_name in self._editable_axes_components.keys():
            editable_component: AxisComponent = self._editable_axes_components[editable_comp_class_name]
            returning_dict[editable_comp_class_name] = editable_component.get_checkboxes_list()
        return returning_dict

    def _get_axes_components_names(self) -> list[str]:
        return list(self._editable_axes_components.keys())

class InheritanceWidget(QWidget):

    def __init__(self, napari_viewer: "ViewerModel", parent: QWidget | None = None):
        super().__init__(parent)
        self._napari_viewer = napari_viewer

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))

        self._inheritance_layer_label = QLabel("Inheriting from layer")
        self._inheritance_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._inheritance_layer_label.setStyleSheet("font-weight: bold;")
        self._inheritance_layer_name = QLabel("None selected")
        self._inheritance_layer_name.setWordWrap(False)
        
        label_container = QWidget()
        label_layout = QHBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(self._inheritance_layer_name)
        label_layout.addStretch(1)
        
        self._layer_name_scroll_area = QScrollArea()
        self._layer_name_scroll_area.setWidgetResizable(True)
        self._layer_name_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._layer_name_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._layer_name_scroll_area.setFrameShape(QFrame.NoFrame) # type: ignore
        self._layer_name_scroll_area.setWidget(label_container) 

        self._inheritance_select_layer_button = QPushButton("Set current layer")
        self._inheritance_apply_button = QPushButton("Apply")

        self._layout.addWidget(self._inheritance_layer_label)
        self._layout.addWidget(self._layer_name_scroll_area)
        self._layout.addWidget(self._inheritance_select_layer_button)
        self._layout.addWidget(self._inheritance_apply_button)
        self._layout.addStretch(1)

QWIDGETSIZE_MAX = 4000

class RotatedTextButton(QPushButton):
    def __init__(self, text, *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self.setMinimumWidth(30)
        self.setMaximumWidth(30)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._label_text = text
        self.setText(text)

    def paintEvent(self, event):
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        painter = QPainter(self)
        
        style = self.style()
        style.drawControl(QStyle.ControlElement.CE_PushButtonBevel, opt, painter, self) 
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(opt.palette.buttonText().color())

        painter.translate(0, self.height())
        painter.rotate(-90)
        text_rect = QRect(0, 0, self.height(), self.width())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.text()
        )

class CollapsibleVerticalBox(QWidget):
    _title: str
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._content_area = QWidget()
        self._is_collapsed = True
        self._title = title
        self._active_listeners = False
        self._toggle_button = QPushButton("▶ " + self._title)
        self._toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                font-weight: bold;
                background-color: #2b45ad; /* Darker Blue */
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #182a73; /* Even Darker Blue */
            }
        """)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._toggle_button)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self._toggle_button.clicked.connect(self._toggle_collapsed)

        self._content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)
        self._content_area.setLayout(QVBoxLayout())

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self._content_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(3)

    def setContentWidget(self, widget):
        self._content_area.layout().addWidget(widget)
        
    def _toggle_collapsed(self):
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self._content_area.setMaximumHeight(0)
            self._toggle_button.setText("▶ " + self._title)
            self._content_area.setFixedHeight(0)
        else:
            self._content_area.setMaximumHeight(QWIDGETSIZE_MAX)
            self._toggle_button.setText("▼ " + self._title)

class CollapsibleHorizontalBox(QWidget):
    _title: str
    def __init__(self, title="Horizontal Box", parent=None):
        super().__init__(parent)
        self._content_area = QWidget()
        self._is_collapsed = True
        self._title = title
        self._toggle_button = RotatedTextButton("▶ " + self._title)
        self._toggle_button.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 10px 0;
                font-weight: bold;
                background-color: #2b45ad;
                color: white;
                border: none;
                border-radius: 5px;
                min-width: 30px;
                max-width: 30px;
            }
            QPushButton:hover {
                background-color: #182a73;
            }
        """)


        """
            QPushButton {
                text-align: left;
                padding: 10px;
                font-weight: bold;
                background-color: #2b45ad;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #182a73;
            }
        """

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self._toggle_button)
        main_layout.addWidget(self._content_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(3)
        
        self._toggle_button.clicked.connect(self._toggle_collapsed)

        # self._content_area.setWidgetResizable(True)
        self._content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._content_area.setMaximumWidth(0)
        self._content_area.setMinimumWidth(0)
        self._content_area.setLayout(QHBoxLayout())
        # self._content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setContentWidget(self, widget):
        self._content_area.layout().addWidget(widget)

    def _toggle_collapsed(self):
        self._is_collapsed = not self._is_collapsed
        self._toggle_button.update()
        
        if self._is_collapsed:
            self._content_area.setMaximumWidth(0)
            self._toggle_button.setText("▶ " + self._title)
            self._content_area.setFixedWidth(0)
        else:
            self._content_area.setMaximumWidth(QWIDGETSIZE_MAX)
            self._toggle_button.setText("▼ " + self._title)

# CHANGED_WIDGET_TYPE(Carlos Rodriguez): I changed the widget type from QStackWidget to QWidget since the only implementation at the moment was flipping between editable and not editable metadata and setting the editable widget form enabled to disabled should be enough 
class MetadataWidget(QWidget):

    _selected_layer: "Layer | None"
    _inheritance_layer: "Layer | None"
    _stored_inheritances: dict[str, list[bool]] | None
    _stacked_layout: QStackedLayout
    _vertical_layout: QVBoxLayout | None
    _horizontal_layout: QHBoxLayout | None
    _no_layer_label: QLabel
    _widget_parent: QObject | None
    _vertical_file_metadata_widget: FileMetadataWidget
    _vertical_editable_widget: EditableMetadataWidget
    _vertical_inheritance_widget: InheritanceWidget
    _horizontal_file_metadata_widget: FileMetadataWidget
    _horizontal_editable_widget: EditableMetadataWidget
    _horizontal_inheritance_widget: InheritanceWidget
    _current_orientation: str
    _active_listeners: bool
    _already_shown: bool

    _general_metadata_instance: FileGeneralMetadata
    _axis_metadata_instance: AxisMetadata

    def __init__(self, napari_viewer: "ViewerModel"):
        super().__init__()
        self._viewer = napari_viewer
        self._napari_viewer = napari_viewer
        self._selected_layer = None
        self._inheritance_layer = None
        self._stored_inheritances = None
        self._current_orientation = "none"
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

        self._general_metadata_instance = FileGeneralMetadata(napari_viewer, self)
        self._connect_file_general_metadata_components()

        self._vert_file_general_metadata_container: QWidget = QWidget()
        self._vert_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._vert_file_general_metadata_container.setLayout(self._vert_file_general_metadata_layout)
        self._hori_file_general_metadata_container: QWidget = QWidget()
        self._hori_file_general_metadata_layout: QGridLayout = QGridLayout()
        self._hori_file_general_metadata_container.setLayout(self._hori_file_general_metadata_layout)

        self._axis_metadata_instance = AxisMetadata(napari_viewer, self)

        self._vert_axis_metadata_container: QWidget = QWidget()
        self._vert_axis_metadata_layout: QGridLayout = QGridLayout()
        self._vert_axis_metadata_container.setLayout(self._vert_axis_metadata_layout)
        self._hori_axis_metadata_container: QWidget = QWidget()
        self._hori_axis_metadata_layout: QGridLayout = QGridLayout()
        self._hori_axis_metadata_container.setLayout(self._hori_axis_metadata_layout)

        self._vertical_file_metadata_widget: FileMetadataWidget = FileMetadataWidget(napari_viewer)
        self._vertical_editable_widget: EditableMetadataWidget = EditableMetadataWidget(napari_viewer)
        self._vertical_editable_widget._set_vertical_mode() # type: ignore
        self._vertical_inheritance_widget: InheritanceWidget = InheritanceWidget(napari_viewer)

        self._horizontal_file_metadata_widget: FileMetadataWidget = FileMetadataWidget(napari_viewer)
        self._horizontal_editable_widget: EditableMetadataWidget = EditableMetadataWidget(napari_viewer)
        self._horizontal_editable_widget._set_horizontal_mode() # type: ignore
        self._horizontal_inheritance_widget: InheritanceWidget = InheritanceWidget(napari_viewer)

        self._connect_file_metadata_widgets()
        self._connect_inheritance_widgets()
        self._viewer.layers.events.connect(self._check_inheritance_layer)

        vertical_container: QWidget = QWidget()
        vertical_container.container_orientation = "vertical"
        vertical_container.setLayout(self._vertical_layout)
        self._stacked_layout.addWidget(vertical_container)

        self._collapsible_vertical_file_metadata: CollapsibleVerticalBox = CollapsibleVerticalBox("File metadata")
        # self._collapsible_vertical_file_metadata.setContentWidget(self._vertical_file_metadata_widget) # type: ignore
        self._collapsible_vertical_file_metadata.setContentWidget(self._vert_file_general_metadata_container) # type: ignore
        self._collapsible_vertical_editable_metadata: CollapsibleVerticalBox = CollapsibleVerticalBox("Axes metadata")
        # self._collapsible_vertical_editable_metadata.setContentWidget(self._vertical_editable_widget) # type: ignore
        self._collapsible_vertical_editable_metadata.setContentWidget(self._vert_axis_metadata_container) # type: ignore
        self._collapsible_vertical_inheritance: CollapsibleVerticalBox = CollapsibleVerticalBox("Inheritance")
        self._collapsible_vertical_inheritance.setContentWidget(self._vertical_inheritance_widget) # type: ignore

        self._vertical_layout.addWidget(self._collapsible_vertical_file_metadata)
        self._vertical_layout.addWidget(self._collapsible_vertical_editable_metadata)
        self._vertical_layout.addWidget(self._collapsible_vertical_inheritance)
        self._vertical_layout.addStretch(1)

        horizontal_container: QWidget = QWidget()
        horizontal_container.container_orientation = "horizontal"
        horizontal_container.setLayout(self._horizontal_layout)
        self._stacked_layout.addWidget(horizontal_container)

        self._collapsible_horizontal_file_metadata: CollapsibleHorizontalBox = CollapsibleHorizontalBox("File metadata")
        # self._collapsible_horizontal_file_metadata.setContentWidget(self._horizontal_file_metadata_widget) # type: ignore
        self._collapsible_horizontal_file_metadata.setContentWidget(self._hori_file_general_metadata_container) # type: ignore
        self._collapsible_horizontal_editable_metadata: CollapsibleHorizontalBox = CollapsibleHorizontalBox("Axes metadata")
        # self._collapsible_horizontal_editable_metadata.setContentWidget(self._horizontal_editable_widget) # type: ignore
        self._collapsible_horizontal_editable_metadata.setContentWidget(self._hori_axis_metadata_container) # type: ignore
        self._collapsible_horizontal_inheritance: CollapsibleHorizontalBox = CollapsibleHorizontalBox("Inheritance")
        self._collapsible_horizontal_inheritance.setContentWidget(self._horizontal_inheritance_widget) # type: ignore

        self._horizontal_layout.addWidget(self._collapsible_horizontal_file_metadata)
        self._horizontal_layout.addWidget(self._collapsible_horizontal_editable_metadata)
        self._horizontal_layout.addWidget(self._collapsible_horizontal_inheritance)
        self._horizontal_layout.addStretch(1)

        no_layer_container: QWidget = QWidget()
        no_layer_container.container_orientation = "no_layer"
        no_layer_container.setLayout(self._no_layer_layout)
        self._no_layer_label: QLabel = QLabel("Select a layer to display its metadata")
        self._no_layer_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # type: ignore
        self._no_layer_label.setStyleSheet("font-weight: bold;") # type: ignore
        self._no_layer_layout.addWidget(self._no_layer_label) # type: ignore
        self._no_layer_layout.addStretch(1)
        self._stacked_layout.addWidget(no_layer_container)

        self.setLayout(self._stacked_layout)

        # self._layout.addWidget(self._no_layer_label)

        # self._editable_widget = EditableMetadataWidget(napari_viewer)
        # self._layout.addWidget(self._editable_widget)

        # self._viewer.layers.selection.events.active.connect(
        #     self._on_selected_layers_changed
        # )

        # self._on_selected_layers_changed()

        # self._layout.addStretch(1)

    def _on_selected_layer_name_changed(self) -> None:
        if self._selected_layer is None:
            return
        general_metadata_instance: FileGeneralMetadata = self._general_metadata_instance
        general_metadata_components: dict[str, FileGeneralMetadataComponent] = general_metadata_instance._file_metadata_components_dict # type: ignore
        general_metadata_component: GeneralMetadataComponent
        for general_metadata_component in general_metadata_components.values():
            general_metadata_component.load_entries()

    def _disconnect_layer_params(self, layer: "Layer") -> None:
        layer.events.name.disconnect(self._on_selected_layer_name_changed)

    def _connect_layer_params(self, layer: "Layer") -> None:
        layer.events.name.connect(self._on_selected_layer_name_changed)

    def _on_selected_layers_changed(self) -> None:
        layer: "Layer | None" = None
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

        editable_vert: EditableMetadataWidget = self._vertical_editable_widget
        editable_vert._set_active_listeners(False)
        editable_vert._update_active_layer()
        editable_vert._set_active_listeners(True)
        editable_hori: EditableMetadataWidget = self._horizontal_editable_widget
        editable_hori._set_active_listeners(False)
        editable_hori._update_active_layer()
        editable_hori._set_active_listeners(True)

        file_meta_vert: FileMetadataWidget = self._vertical_file_metadata_widget
        file_meta_vert._set_active_listeners(False)
        file_meta_vert._set_layer(self._selected_layer)
        file_meta_vert._set_active_listeners(True)
        file_meta_hori: FileMetadataWidget = self._horizontal_file_metadata_widget
        file_meta_hori._set_active_listeners(False)
        file_meta_hori._set_layer(self._selected_layer)
        file_meta_hori._set_active_listeners(True)

        self._update_orientation()

    def showEvent(self, a0: QShowEvent | None) -> None:
        
        if self._already_shown:
            return

        super().showEvent(a0)

        parent_widget = self.parent()
        if parent_widget is None:
            return
        if isinstance(parent_widget, QDockWidget):
            napari_viewer: "ViewerModel" = self._viewer
            if napari_viewer is None:
                return
            napari_viewer = cast("ViewerModel", napari_viewer)
            self._on_selected_layers_changed()
            self._widget_parent = parent_widget
            self._update_orientation()

            napari_viewer.layers.selection.events.active.connect(self._on_selected_layers_changed)
            self._widget_parent.dockLocationChanged.connect(self._on_dock_location_changed)

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
        if dock_widget is None:
            return "vertical"
        elif not isinstance(dock_widget, QDockWidget):
            return "vertical"
        else:
            main_window: QMainWindow = cast(QMainWindow, dock_widget.parent())
            dock_area: Qt.DockWidgetArea = main_window.dockWidgetArea(dock_widget)
            if dock_area == Qt.DockWidgetArea.LeftDockWidgetArea or dock_area == Qt.DockWidgetArea.RightDockWidgetArea or dock_widget.isFloating():
                return "vertical"
        return "horizontal"

    def _update_orientation(self) -> None:
        self._store_inheritances()
        self._vertical_editable_widget._update_active_layer()
        self._horizontal_editable_widget._update_active_layer()
        if not self._active_listeners:
            return
        self._active_listeners = False
        required_orientation: str = self._get_required_orientation()
        selected_layer: "Layer | None" = self._selected_layer
        if selected_layer is None:
            required_orientation = "no_layer"
        if required_orientation == self._current_orientation:
            self._active_listeners = True
            self._restore_inheritances()
            return
        elif required_orientation == "vertical":
            self._set_layout_type("vertical")
        elif required_orientation == "horizontal":
            self._set_layout_type("horizontal")
        else: 
            self._set_layout_type("no_layer")
        self._active_listeners = True

        self._restore_inheritances()

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
        current_row: int  = starting_row

        vert_file_layout: QGridLayout = self._vert_file_general_metadata_layout
        hori_file_layout: QGridLayout = self._hori_file_general_metadata_layout

        file_general_meta_instance: FileGeneralMetadata = self._general_metadata_instance
        components_dict = file_general_meta_instance._file_metadata_components_dict # type: ignore

        if orientation == "vertical":

            self._reset_layout(hori_file_layout)

            for name in components_dict.keys():

                current_column: int = starting_column

                total_row_spans: int = 0
                total_column_spans: int = 0

                general_component: GeneralMetadataComponent = components_dict[name]

                general_component_qlabel: QLabel = general_component._component_qlabel
                vert_file_layout.addWidget(general_component_qlabel, current_row, current_column, 1, 1)
                

                general_component.load_entries()
                entries_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = general_component.get_entries_dict(orientation) # type: ignore

                if general_component.get_under_label(orientation):
                    current_row += 1
                else:
                    current_column += 1

                total_row_spans += 1

                for entry_name in entries_dict.keys():
                    entry_widget: QWidget = entries_dict[entry_name][0]
                    row_span: int = entries_dict[entry_name][1]
                    column_span: int = entries_dict[entry_name][2]
                    method_name: str = entries_dict[entry_name][3]
                    alignment: Qt.AlignmentFlag | None = entries_dict[entry_name][4]
                    if alignment is None:
                        alignment = Qt.AlignmentFlag.AlignLeft
                    
                    vert_file_layout.addWidget(entry_widget, current_row, current_column, row_span, column_span, alignment) # type: ignore
                    current_row += row_span
        else:

            self._reset_layout(vert_file_layout)

            for name in components_dict.keys():

                current_column: int = starting_column

                total_row_spans: int = 0
                total_column_spans: int = 0

                general_component: GeneralMetadataComponent = components_dict[name] # type: ignore

                general_component_qlabel: QLabel = general_component._component_qlabel # type: ignore
                hori_file_layout.addWidget(general_component_qlabel, current_row, current_column, 1, 1) # type: ignore

                general_component.load_entries()
                entries_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = general_component.get_entries_dict(orientation) # type: ignore

                if general_component.get_under_label(orientation):
                    current_row += 1
                else:
                    current_column += 1

                total_row_spans += 1

                for entry_name in entries_dict.keys():
                    entry_widget: QWidget = entries_dict[entry_name][0]
                    row_span: int = entries_dict[entry_name][1]
                    column_span: int = entries_dict[entry_name][2]
                    method_name: str = entries_dict[entry_name][3]
                    alignment: Qt.AlignmentFlag | None = entries_dict[entry_name][4]
                    if alignment is None:
                        alignment = Qt.AlignmentFlag.AlignLeft

                    hori_file_layout.addWidget(entry_widget, current_row, current_column, row_span, column_span, alignment)
                    current_row += row_span

        for vert_file_layout_row in range(vert_file_layout.rowCount()):
            vert_file_layout.setRowStretch(vert_file_layout_row, 0)
        vert_file_layout.setRowStretch(vert_file_layout.rowCount(), 1)
        for vert_file_layout_column in range(vert_file_layout.columnCount()):
            vert_file_layout.setColumnStretch(vert_file_layout_column, 0)
        vert_file_layout.setColumnStretch(vert_file_layout.columnCount()-1, 1)
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
        components_dict = axis_meta_instance._axis_metadata_components_dict # type: ignore

        spacer_places_list: list[int] = []

        if orientation == "vertical":

            self._reset_layout(vert_axis_layout)

            #This is the name of every axis
            for name in components_dict.keys():

                current_column: int = starting_column

                total_row_spans: int = 0
                total_column_spans: int = 0

                #This is the instance of the Axis Protocol
                axis_component: MetadataComponent = components_dict[name] # type: ignore

                axis_component_qlabel: QLabel = axis_component._component_qlabel # type: ignore
                vert_axis_layout.addWidget(axis_component_qlabel, current_row, current_column, 1, 1) # type: ignore

                current_column += 1

                axis_component.load_entries()
                ## TODO: After adding the entries, they need to be connected because of the creating of the axis widgets from scratch when the layer changes.
                #Probably better to call it from within the AxisComponent class because I don't know if they're created or not by this point. 
                entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = axis_component.get_entries_dict(orientation) # type: ignore

                total_axis_index_row_spans: int = 0

                for axis_index in entries_dict.keys():

                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = entries_dict[axis_index] # type: ignore

                    for widget_name in axis_entries_dict.keys():
                        entry_widget: QWidget = axis_entries_dict[widget_name][0]
                        entry_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        method_name: str = axis_entries_dict[widget_name][3]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[widget_name][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft

                        vert_axis_layout.addWidget(entry_widget, current_row, setting_column, row_span, column_span)
                        setting_column += column_span

                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span


                    current_row += max_axis_index_row_span

                # if it is not the last axis:
                if name != list(components_dict.keys())[-1]:

                    spacer_places_list.append(current_row)

                    current_row += 3
                    
                    # before_spacer = QWidget()
                    # before_spacer.setFixedHeight(2)
                    # before_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    # vert_axis_layout.addWidget(before_spacer, current_row, 0, 1, row_col_sums[1])
                    # current_row += 1

                    # axis_spacer = QFrame()
                    # axis_spacer.setFrameShape(QFrame.Shape.HLine)
                    # axis_spacer.setFrameShadow(QFrame.Shadow.Sunken)
                    # axis_spacer.setStyleSheet("color: #999; background-color: #999;")
                    # axis_spacer.setFixedHeight(3)
                    # axis_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    # vert_axis_layout.addWidget(axis_spacer, current_row, 0, 1, row_col_sums[1])
                    # current_row += 1

                    # after_spacer = QWidget()
                    # after_spacer.setFixedHeight(2)
                    # after_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    # vert_axis_layout.addWidget(after_spacer, current_row, 0, 1, row_col_sums[1])
                    # current_row += 1

        elif orientation == "horizontal":

            self._reset_layout(hori_axis_layout)

            #This is the name of every axis
            for name in components_dict.keys():

                current_column: int = starting_column
                current_row: int = starting_row

                total_row_spans: int = 0
                total_column_spans: int = 0

                #This is the instance of the Axis Protocol
                axis_component: MetadataComponent = components_dict[name] # type: ignore

                axis_component_qlabel: QLabel = axis_component._component_qlabel # type: ignore
                axis_component_qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
                adding_label_column = current_column

                current_row += 1

                axis_component.load_entries()
                ## TODO: After adding the entries, they need to be connected because of the creating of the axis widgets from scratch when the layer changes.
                #Probably better to call it from within the AxisComponent class because I don't know if they're created or not by this point. 
                entries_dict: dict[int, dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]] = axis_component.get_entries_dict(orientation) # type: ignore

                max_axis_row_spans: int = 0
                max_axis_col_spans: int = 0

                for axis_index in entries_dict.keys():

                    current_axis_col_sum: int = 0

                    setting_column = current_column

                    max_axis_index_row_span: int = 0

                    axis_entries_dict: dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]] = entries_dict[axis_index] # type: ignore

                    for widget_name in axis_entries_dict.keys():
                        entry_widget: QWidget = axis_entries_dict[widget_name][0]
                        entry_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        row_span: int = axis_entries_dict[widget_name][1]
                        column_span: int = axis_entries_dict[widget_name][2]
                        method_name: str = axis_entries_dict[widget_name][3]
                        alignment: Qt.AlignmentFlag | None = axis_entries_dict[widget_name][4]
                        if alignment is None:
                            alignment = Qt.AlignmentFlag.AlignLeft

                        hori_axis_layout.addWidget(entry_widget, current_row, setting_column, row_span, column_span)
                        setting_column += column_span

                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span

                        current_axis_col_sum += column_span

                        if row_span > max_axis_index_row_span:
                            max_axis_index_row_span = row_span

                    if current_axis_col_sum > max_axis_col_spans:
                        max_axis_col_spans = current_axis_col_sum

                    current_row += max_axis_index_row_span
                
                hori_axis_layout.addWidget(axis_component_qlabel, 0, adding_label_column, 1, 1) # type: ignore

                

                ## if it is not the last axis:
                if name != list(components_dict.keys())[-1]:
                    spacer_places_list.append(starting_column + max_axis_col_spans)

                    # setting_column = starting_column + max_axis_col_spans
                    # before_spacer = QWidget()
                    # before_spacer.setFixedWidth(2)
                    # before_spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                    # before_spacer.setStyleSheet("color: #999; background-color: #999;")
                    # hori_axis_layout.addWidget(before_spacer, 0, setting_column, row_col_sums[0], 1)
                    # current_column += 1

                    # axis_spacer = QFrame()
                    # axis_spacer.setFrameShape(QFrame.Shape.VLine)
                    # axis_spacer.setFrameShadow(QFrame.Shadow.Sunken)
                    # axis_spacer.setStyleSheet("color: #999; background-color: #999;")
                    # axis_spacer.setFixedWidth(5)
                    # axis_spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                    # hori_axis_layout.addWidget(axis_spacer, 0, setting_column + 1, row_col_sums[0], 1)
                    # current_column += 1

                    # after_spacer = QWidget()
                    # after_spacer.setFixedWidth(2)
                    # after_spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                    # after_spacer.setStyleSheet("color: #999; background-color: #999;")
                    # hori_axis_layout.addWidget(after_spacer, 0, setting_column + 2, row_col_sums[0], 1)
                    # current_column += 1

                starting_column += max_axis_col_spans + 3

        number_of_rows = 0
        number_of_cols = 0
        if orientation == "vertical":
            number_of_rows = vert_axis_layout.rowCount()
            number_of_cols = vert_axis_layout.columnCount()
        elif orientation == "horizontal":
            number_of_rows = hori_axis_layout.rowCount()
            number_of_cols = hori_axis_layout.columnCount()

        for spacer_position in spacer_places_list:

            if orientation == "vertical":
                before_spacer_item = QWidget()
                before_spacer_item.setFixedHeight(2)
                before_spacer_item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                vert_axis_layout.addWidget(before_spacer_item, spacer_position, 0, 1, number_of_cols)

                spacer_item = QFrame()
                spacer_item.setFrameShape(QFrame.Shape.HLine)
                spacer_item.setFrameShadow(QFrame.Shadow.Sunken)
                spacer_item.setStyleSheet("color: #999; background-color: #999;")
                spacer_item.setFixedHeight(3)
                spacer_item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                vert_axis_layout.addWidget(spacer_item, spacer_position + 1, 0, 1, number_of_cols)

                after_spacer_item = QWidget()
                after_spacer_item.setFixedHeight(2)
                after_spacer_item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                vert_axis_layout.addWidget(after_spacer_item, spacer_position + 2, 0, 1, number_of_cols)

            elif orientation == "horizontal":
                before_spacer_item = QWidget()
                before_spacer_item.setFixedWidth(2)
                before_spacer_item.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                hori_axis_layout.addWidget(before_spacer_item, 0, spacer_position, number_of_rows, 1)

                spacer_item = QFrame()
                spacer_item.setFrameShape(QFrame.Shape.VLine)
                spacer_item.setFrameShadow(QFrame.Shadow.Sunken)
                spacer_item.setStyleSheet("color: #999; background-color: #999;")
                spacer_item.setFixedWidth(3)
                spacer_item.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                hori_axis_layout.addWidget(spacer_item, 0, spacer_position + 1, number_of_rows, 1)

                after_spacer_item = QWidget()
                after_spacer_item.setFixedWidth(2)
                after_spacer_item.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                hori_axis_layout.addWidget(after_spacer_item, 0, spacer_position + 2, number_of_rows, 1)

        if orientation == "vertical":        
            for row in range(vert_axis_layout.rowCount()):
                vert_axis_layout.setRowStretch(row, 0)
            vert_axis_layout.setRowStretch(vert_axis_layout.rowCount(), 1)
            for column in range(vert_axis_layout.columnCount()):
                vert_axis_layout.setColumnStretch(column, 0)
            vert_axis_layout.setColumnStretch(vert_axis_layout.columnCount(), 1)
        else: 
            for row in range(hori_axis_layout.rowCount()):
                hori_axis_layout.setRowStretch(row, 0)
            hori_axis_layout.setRowStretch(hori_axis_layout.rowCount(), 1)
            for column in range(hori_axis_layout.columnCount()):
                hori_axis_layout.setColumnStretch(column, 0)
            hori_axis_layout.setColumnStretch(hori_axis_layout.columnCount()-1, 1)

    def _connect_file_general_metadata_components(self) -> None:

        file_general_meta_instance: FileGeneralMetadata = self._general_metadata_instance
        components_dict = file_general_meta_instance._file_metadata_components_dict # type: ignore

        for name in components_dict.keys():
            general_component: GeneralMetadataComponent = components_dict[name] # type: ignore
            entries_dict: dict[str, tuple[QWidget, int, int, str]] = general_component.get_entries_dict(self._current_orientation)
            for entry_name in entries_dict.keys():
                entry_widget: QWidget = entries_dict[entry_name][0]
                method_name: str = entries_dict[entry_name][3]
                if method_name == "":
                    continue
                if isinstance(entry_widget, QLineEdit):
                    entry_line_edit: QLineEdit = cast(QLineEdit, entry_widget)
                    entry_line_edit.textEdited.connect(getattr(self, method_name))

    def _connect_axis_metadata_components(self) -> None:

        axis_general_meta_instance: AxisComponent

    def _on_name_line_changed(self, text: str) -> None:
        sender_line_edit: QLineEdit = cast(QLineEdit, self.sender())
        active_layer: "Layer | None" = get_active_layer(self._napari_viewer) # type: ignore
        if active_layer is None:
            sender_line_edit.setText("No layer selected")
            return
        if text == active_layer.name:
            return
        active_layer.name = text

    def _set_layout_type(self, layout_type: str) -> None:

        if layout_type == "vertical":
            self._set_general_metadata_orientation("vertical")
            self._set_axis_metadata_orientation("vertical")
        elif layout_type == "horizontal": 
            self._set_general_metadata_orientation("horizontal")
            self._set_axis_metadata_orientation("horizontal")

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

    def _connect_file_metadata_widgets(self) -> None:
        file_meta_vert: FileMetadataWidget = self._vertical_file_metadata_widget
        file_meta_hori: FileMetadataWidget = self._horizontal_file_metadata_widget
        
        vert_layer_name_line_edit: QLineEdit = file_meta_vert._layer_name_QLineEdit
        vert_layer_name_line_edit.textEdited.connect(self._layer_name_line_edited)

        hori_layer_name_line_edit: QLineEdit = file_meta_hori._layer_name_QLineEdit
        hori_layer_name_line_edit.textEdited.connect(self._layer_name_line_edited)

    def _layer_name_line_edited(self, text: str) -> None:

        file_meta: FileMetadataWidget = cast(FileMetadataWidget, cast(QLineEdit, self.sender()).parent())
        if not file_meta._active_listeners:
            return
        current_layer: "Layer | None" = self._selected_layer
        if current_layer is None:
            return
        if current_layer.name == text:
            return
        self._vertical_file_metadata_widget._active_listeners = False
        self._horizontal_file_metadata_widget._active_listeners = False
        current_layer.name = text
        if file_meta == self._vertical_file_metadata_widget:
            self._horizontal_file_metadata_widget._layer_name_QLineEdit.setText(text)
        else:
            self._vertical_file_metadata_widget._layer_name_QLineEdit.setText(text)
        self._vertical_file_metadata_widget._active_listeners = True
        self._horizontal_file_metadata_widget._active_listeners = True

    def _connect_inheritance_widgets(self) -> None:
        inherit_vert: InheritanceWidget = self._vertical_inheritance_widget
        inherit_hori: InheritanceWidget = self._horizontal_inheritance_widget

        inherit_vert_select_layer_button: QPushButton = inherit_vert._inheritance_select_layer_button
        inherit_vert_select_layer_button.clicked.connect(self._inheritance_select_layer_button_clicked)

        inherit_hori_select_layer_button: QPushButton = inherit_hori._inheritance_select_layer_button
        inherit_hori_select_layer_button.clicked.connect(self._inheritance_select_layer_button_clicked)

        inherit_vert_apply_button: QPushButton = inherit_vert._inheritance_apply_button
        inherit_vert_apply_button.clicked.connect(self._inheritance_apply_button_clicked)

        inherit_hori_apply_button: QPushButton = inherit_hori._inheritance_apply_button
        inherit_hori_apply_button.clicked.connect(self._inheritance_apply_button_clicked)

    def _inheritance_select_layer_button_clicked(self) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            self._inheritance_layer: "Layer | None" = None
        else:
            self._inheritance_layer: "Layer | None" = current_layer
        self._update_inheritance_widget()
        
    def _update_inheritance_widget(self) -> None:
        inherit_vert: InheritanceWidget = self._vertical_inheritance_widget
        inherit_hori: InheritanceWidget = self._horizontal_inheritance_widget
        
        inherit_vert_layer_name: QLabel = inherit_vert._inheritance_layer_name
        inherit_hori_layer_name: QLabel = inherit_hori._inheritance_layer_name

        if self._inheritance_layer is None:
            with QSignalBlocker(inherit_vert_layer_name):
                inherit_vert_layer_name.setText("None selected")
            with QSignalBlocker(inherit_hori_layer_name):
                inherit_hori_layer_name.setText("None selected")
            return
        
        with QSignalBlocker(inherit_vert_layer_name):
            inherit_vert_layer_name.setText(self._inheritance_layer.name)
        with QSignalBlocker(inherit_hori_layer_name):
            inherit_hori_layer_name.setText(self._inheritance_layer.name)

    def _check_inheritance_layer(self) -> None:
        if self._inheritance_layer is None:
            return
        if self._inheritance_layer not in self._viewer.layers:
            self._inheritance_layer = None
        
        self._update_inheritance_widget()

    def _inheritance_apply_button_clicked(self) -> None:
        if self._inheritance_layer is None:
            return
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        if self._inheritance_layer is current_layer:
            return
        inheritance_layer_dims: str = self._inheritance_layer.ndim
        current_layer_dims = current_layer.ndim
        if inheritance_layer_dims != current_layer_dims:
            print("Inheritance layer must have same number of dimensions as current layer")
            return
        inheritance_axes_labels = get_axes_labels(self._viewer, self._inheritance_layer)
        inheritance_translation = get_axes_translations(self._viewer, self._inheritance_layer)
        inheritance_axes_scales = get_axes_scales(self._viewer, self._inheritance_layer)
        inheritance_axes_units = get_axes_units(self._viewer, self._inheritance_layer)

        editing_dict = {}
        getting_from_widget: QWidget | None = None
        required_orientation: str = self._get_required_orientation()
        if required_orientation == "vertical":
            getting_from_widget = self._vertical_editable_widget
        else:
            getting_from_widget = self._horizontal_editable_widget
        axes_components_names: list[str] = getting_from_widget._get_axes_components_names() # type: ignore
        for component_name in axes_components_names:
            editing_dict[component_name] = getting_from_widget._editable_axes_components[component_name].get_entries_dict()
        
        for component_name in editing_dict.keys():
            for axis_number in editing_dict[component_name].keys():
                inheritance_checkbox: QCheckBox = editing_dict[component_name][axis_number]["InheritCheckBox"][2]
                if inheritance_checkbox.isChecked():
                    if component_name == "AxesLabels":
                        setting_line_edit: QLineEdit = editing_dict[component_name][axis_number]["AxisLabel"][2]
                        setting_value = inheritance_axes_labels[axis_number]
                        setting_line_edit.setText(setting_value)
                        getting_from_widget._on_axes_label_changed()
                    elif component_name == "AxesTranslations":
                        setting_spin_box: QDoubleSpinBox = editing_dict[component_name][axis_number]["AxisTranslate"][2]
                        setting_value = inheritance_translation[axis_number]
                        setting_spin_box.setValue(setting_value)
                    elif component_name == "AxesScales":
                        setting_spin_box: QDoubleSpinBox = editing_dict[component_name][axis_number]["AxisScale"][2]
                        setting_value = inheritance_axes_scales[axis_number]
                        setting_spin_box.setValue(setting_value)
                    elif component_name == "AxesUnits":
                        setting_combo_box: QComboBox = editing_dict[component_name][axis_number]["AxisUnit"][2]
                        type_combo_box: QComboBox = editing_dict[component_name][axis_number]["AxisType"][2]
                        type_combo_box.setCurrentText("string")
                        setting_value = str(inheritance_axes_units[axis_number])
                        setting_combo_box.setCurrentText(setting_value)
 
    def _editable_checkbox_state_changed(self, layout_mode: str) -> None:
        current_layer: "Layer | None" = get_active_layer(self._viewer)
        if current_layer is None:
            return
        check_boxes_dict: dict[str, dict[str, list[QCheckBox]]] = {
            "hori":{},
            "vert":{}
        }
        check_boxes_dict["hori"] = self._horizontal_editable_widget._get_checkboxes_dict()
        check_boxes_dict["vert"] = self._vertical_editable_widget._get_checkboxes_dict()

        if layout_mode == "vertical":
            for axis_component in check_boxes_dict["vert"].keys():
                vert_list_of_checkboxes: list[QCheckBox] = check_boxes_dict["vert"][axis_component]
                hori_list_of_checkboxes: list[QCheckBox] = check_boxes_dict["hori"][axis_component]
                for checkbox_index, checkbox in enumerate(vert_list_of_checkboxes):
                    with QSignalBlocker(hori_list_of_checkboxes[checkbox_index]):
                        hori_list_of_checkboxes[checkbox_index].setChecked(checkbox.isChecked())
        else:
            for axis_component in check_boxes_dict["hori"].keys():
                vert_list_of_checkboxes: list[QCheckBox] = check_boxes_dict["vert"][axis_component]
                hori_list_of_checkboxes: list[QCheckBox] = check_boxes_dict["hori"][axis_component]
                for checkbox_index, checkbox in enumerate(hori_list_of_checkboxes):
                    with QSignalBlocker(vert_list_of_checkboxes[checkbox_index]):
                        vert_list_of_checkboxes[checkbox_index].setChecked(checkbox.isChecked())

    def _store_inheritances(self) -> None:
        stored_inheritances: dict[str, list[bool]] = {}
        axes_components: list[str] = self._vertical_editable_widget._get_axes_components_names()
        for axes_component in axes_components:
            stored_inheritances[axes_component] = []
            for checkbox in self._vertical_editable_widget._get_checkboxes_dict()[axes_component]:
                stored_inheritances[axes_component].append(checkbox.isChecked())
        self._stored_inheritances = stored_inheritances

    def _restore_inheritances(self) -> None:
        if self._store_inheritances is None:
            return
        check_boxes_dict: dict[str, dict[str, list[QCheckBox]]] = {
            "hori":{},
            "vert":{}
        }
        check_boxes_dict["hori"] = self._horizontal_editable_widget._get_checkboxes_dict()
        check_boxes_dict["vert"] = self._vertical_editable_widget._get_checkboxes_dict()

        first_axes_component: str = list(check_boxes_dict["hori"].keys())[0]
        length_of_checkboxes_list: int = len(check_boxes_dict["hori"][first_axes_component])
        if length_of_checkboxes_list != len(self._stored_inheritances[first_axes_component]):
            return

        for layout_mode in check_boxes_dict.keys():
            for axes_component in check_boxes_dict[layout_mode].keys():
                for checkbox_index, checkbox in enumerate(check_boxes_dict[layout_mode][axes_component]):
                    with QSignalBlocker(checkbox):
                        checkbox.setChecked(self._stored_inheritances[axes_component][checkbox_index])

    #def _remove_dock_widget(self) -> None:
    #    # To constrain our implementation and for testing, we only want
    #    # the type of _viewer to be ViewerModel and not Viewer.
    #    # This works around that typing information.
    #    if window := getattr(self._viewer, "window", None):
    #        window.remove_dock_widget(self)

