from typing import TYPE_CHECKING

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import QLabel, QLineEdit, QSizePolicy, QTextEdit, QWidget

from napari_metadata._file_size import generate_display_size
from napari_metadata._model import (
    get_layer_data_dtype,
    get_layer_data_shape,
    get_layer_source_path,
    resolve_layer,
)
from napari_metadata._protocols import MetadataComponent

if TYPE_CHECKING:
    from napari.layers import Layer
    from napari.viewer import ViewerModel

FILE_METADATA_COMPONENTS_DICT: dict[str, type[MetadataComponent]] = {}


def _metadata_component(
    _setting_class: type[MetadataComponent],
) -> type[MetadataComponent]:
    """This decorator is used to register the MetadataComponent
    class in the METADATA_COMPONENTS_DICT dictionary.
    """
    FILE_METADATA_COMPONENTS_DICT[_setting_class.__name__] = _setting_class
    return _setting_class


@_metadata_component
class LayerNameComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool

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
        self._layer_name_line_edit.editingFinished.connect(
            self._on_name_line_changed
        )
        self._component_name = 'LayerName'

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = None
        if layer is not None:
            active_layer = layer
        else:
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore
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

    def _on_name_line_changed(self) -> None:
        line_edit: QLineEdit = self._layer_name_line_edit
        text: str = line_edit.text()
        active_layer: Layer | None = resolve_layer(self._napari_viewer)  # type: ignore
        if active_layer is None:
            line_edit.setText('No layer selected')
            return
        if text == active_layer.name:
            return
        active_layer.name = text


@_metadata_component
class LayerShapeComponent:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel
    _under_label: bool

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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore
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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore
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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore
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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore
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


class FileGeneralMetadata:
    """This is the class that integrates all of the general metadata components together and instantiates them. This class itself
    is instantiated in the MetadataWidgetAPI class, which is ultimately the main class passed to napari. This class will only hold the
    components instances and everything else is handled in the MetadataWidgetAPI class or the individual metadata component classes.
    """

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
        ) in FILE_METADATA_COMPONENTS_DICT.items():
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
