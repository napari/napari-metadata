"""Contains the axis metadata widgets along with the AxisMetadata class that
incorporates all widget instances.
"""

# TODO:Add docstring about classes, injections and definitions

from typing import TYPE_CHECKING, cast

import pint
from napari.utils.notifications import show_error
from qtpy.QtCore import QSignalBlocker, Qt
from qtpy.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QWidget,
)

from napari_metadata.layer_utils import (
    get_axes_labels,
    get_axes_scales,
    get_axes_translations,
    get_axes_units,
    get_layer_dimensions,
    resolve_layer,
    set_axes_labels,
    set_axes_scales,
    set_axes_translations,
    set_axes_units,
)
from napari_metadata.units import AxisUnitEnum
from napari_metadata.widgets._protocols import (
    AxesMetadataComponentsInstanceAPI,
    AxisComponent,
    MetadataWidgetAPI,
)

if TYPE_CHECKING:
    from napari.layers import Layer
    from napari.viewer import ViewerModel

INHERIT_STRING = ''


AXIS_METADATA_COMPONENTS_DICT: dict[str, type[AxisComponent]] = {}


def _axis_metadata_component(
    _setting_class: type[AxisComponent],
) -> type[AxisComponent]:
    """This decorator is used to register the MetadataComponent
    class in the METADATA_COMPONENTS_DICT dictionary
    """

    def reset_tuples_injection(self: AxisComponent) -> None:
        tuple_names = [name for name in vars(self) if name.endswith('_tuple')]
        if not tuple_names:
            return
        current_tuple_values = tuple(
            getattr(self, tuple_name) for tuple_name in tuple_names
        )
        new_values = _reset_widget_tuples(*current_tuple_values)
        for tuple_name, new_value in zip(tuple_names, new_values, strict=True):
            setattr(self, tuple_name, new_value)

    _setting_class._reset_tuples = reset_tuples_injection

    def set_axis_name_labels_injection(self: AxisComponent) -> None:
        if self._component_name == 'AxisLabels':
            return
        current_axis_names: tuple[str, ...] = get_axes_labels(
            self._napari_viewer
        )
        for axis_index, axis_label in enumerate(current_axis_names):
            current_axis_name_label = self._axis_name_labels_tuple[axis_index]
            if axis_label == '':
                current_axis_name_label.setText(f'{axis_index}')
            else:
                current_axis_name_label.setText(axis_label)

    _setting_class._set_axis_name_labels = set_axis_name_labels_injection

    def set_checkboxes_visibility_injection(
        self: AxisComponent, visible: bool
    ) -> None:
        checkbox_tuple = self._inherit_checkbox_tuple
        for checkbox in checkbox_tuple:
            checkbox.setVisible(visible)

    _setting_class._set_checkboxes_visibility = (
        set_checkboxes_visibility_injection
    )

    AXIS_METADATA_COMPONENTS_DICT[_setting_class.__name__] = _setting_class
    return _setting_class


AXES_ENTRIES_DICT: dict[str, type[AxisComponent]] = {}


def _reset_widget_tuples(*args: tuple[QWidget, ...]):
    for tuple_of_widgets in args:
        for widget in tuple_of_widgets:
            widget.setParent(None)
            widget.deleteLater()
    return tuple(() for _ in range(len(args)))


@_axis_metadata_component
class AxisLabels:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _name_line_edit_tuple: tuple[QLineEdit, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]
    _selected_layer: 'Layer | None'

    _NAME_LINE_EDIT_CALLING_METHOD = '_on_axis_labels_lines_edited'

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
        self._selected_layer = None

        self._axis_name_labels_tuple = ()
        self._name_line_edit_tuple = ()
        self._inherit_checkbox_tuple = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer: Layer | None = resolve_layer(self._napari_viewer, layer)
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return
        layer_labels = get_axes_labels(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_labels)):
            with QSignalBlocker(self._name_line_edit_tuple[i]):
                self._name_line_edit_tuple[i].setText(layer_labels[i])

    def get_entries_dict(
        self,
    ) -> dict[
        int,
        dict[
            str, tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None]
        ],
    ]:
        returning_dict: dict[
            int,
            dict[
                str,
                tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None],
            ],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['index_label'] = (
                [self._axis_name_labels_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['name_line_edit'] = (
                [self._name_line_edit_tuple[i]],
                1,
                1,
                self._NAME_LINE_EDIT_CALLING_METHOD,
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                [self._inherit_checkbox_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def _reset_tuples(self) -> None: ...

    def _set_axis_name_labels(self) -> None: ...

    def _set_checkboxes_visibility(self, visible: bool) -> None:
        _ = visible

    def get_line_edit_labels(self) -> tuple[str, ...]:
        return tuple(
            self._name_line_edit_tuple[i].text()
            for i in range(len(self._name_line_edit_tuple))
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
        self._axis_name_labels_tuple = setting_index_tuple
        self._name_line_edit_tuple = setting_name_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        for name_line_edit in self._name_line_edit_tuple:
            name_line_edit.editingFinished.connect(
                self._on_line_edit_finished_edited
            )

    def _on_line_edit_finished_edited(self) -> None:
        line_edits_text: tuple[str, ...] = self.get_line_edit_labels()
        set_axes_labels(
            self._napari_viewer, line_edits_text, self._selected_layer
        )
        main_widget_api: MetadataWidgetAPI = cast(
            MetadataWidgetAPI, self._main_widget
        )
        meta_data_instances: AxesMetadataComponentsInstanceAPI = (
            main_widget_api.get_axes_metadata_instance()
        )
        meta_data_instances._update_axes_labels()

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = resolve_layer(self._napari_viewer)
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
        set_axes_labels(self._napari_viewer, tuple(setting_labels))  # type: ignore
        self._selected_layer = None


@_axis_metadata_component
class AxisTranslations:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel

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
        self._selected_layer = None

        self._axis_name_labels_tuple: tuple[QLabel, ...] = ()
        self._translation_spinbox_tuple: tuple[QDoubleSpinBox, ...] = ()
        self._inherit_checkbox_tuple: tuple[QCheckBox, ...] = ()

    def load_entries(self, layer: 'Layer | None' = None) -> None:
        active_layer = resolve_layer(self._napari_viewer, layer)
        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_translates = get_axes_translations(
            self._napari_viewer, active_layer
        )
        for i in range(len(layer_translates)):
            with QSignalBlocker(self._translation_spinbox_tuple[i]):
                self._translation_spinbox_tuple[i].setValue(
                    layer_translates[i]
                )

    def get_entries_dict(
        self,
    ) -> dict[
        int,
        dict[
            str, tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None]
        ],
    ]:
        returning_dict: dict[
            int,
            dict[
                str,
                tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None],
            ],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                [self._axis_name_labels_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['translate_spinbox'] = (
                [self._translation_spinbox_tuple[i]],
                1,
                1,
                '_on_axis_translate_spin_box_adjusted',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                [self._inherit_checkbox_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def _reset_tuples(self) -> None: ...

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = _get_axis_label_tuple(
            self._napari_viewer, layer
        )
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
        )
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        self._axis_name_labels_tuple = setting_name_tuple
        self._translation_spinbox_tuple = setting_translation_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        for translation_spinbox in self._translation_spinbox_tuple:
            translation_spinbox.valueChanged.connect(
                self._on_spinbox_value_changed
            )

    def _set_axis_name_labels(self) -> None: ...

    def _set_checkboxes_visibility(self, visible: bool) -> None:
        _ = visible

    def _on_spinbox_value_changed(self) -> None:
        spin_box_values: tuple[float, ...] = self._get_spin_box_values()
        set_axes_translations(
            self._napari_viewer, spin_box_values, self._selected_layer
        )

    def _get_spin_box_values(self) -> tuple[float, ...]:
        return tuple(
            self._translation_spinbox_tuple[i].value()
            for i in range(len(self._translation_spinbox_tuple))
        )

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = resolve_layer(self._napari_viewer)
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
        set_axes_translations(self._napari_viewer, tuple(setting_translates))  # type: ignore
        self._selected_layer = None


@_axis_metadata_component
class AxisScales:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel

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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_scales = get_axes_scales(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_scales)):
            with QSignalBlocker(self._scale_spinbox_tuple[i]):
                self._scale_spinbox_tuple[i].setValue(layer_scales[i])

    def get_entries_dict(
        self,
    ) -> dict[
        int,
        dict[
            str, tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None]
        ],
    ]:
        returning_dict: dict[
            int,
            dict[
                str,
                tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None],
            ],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                [self._axis_name_labels_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['scale_spinbox'] = (
                [self._scale_spinbox_tuple[i]],
                1,
                1,
                '_on_axis_scale_spin_box_adjusted',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                [self._inherit_checkbox_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def _reset_tuples(self) -> None: ...

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

        for scale_spinbox in self._scale_spinbox_tuple:
            scale_spinbox.valueChanged.connect(
                self._on_axis_scale_spin_box_adjusted
            )

    def _set_axis_name_labels(self) -> None: ...

    def _set_checkboxes_visibility(self, visible: bool) -> None:
        _ = visible

    def _on_axis_scale_spin_box_adjusted(self) -> None:
        spin_box_values: tuple[float, ...] = self.get_spin_box_values()
        set_axes_scales(
            self._napari_viewer, spin_box_values, self._selected_layer
        )

    def get_spin_box_values(self) -> tuple[float, ...]:
        return tuple(
            self._scale_spinbox_tuple[i].value()
            for i in range(len(self._scale_spinbox_tuple))
        )

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = resolve_layer(self._napari_viewer)
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
        set_axes_scales(self._napari_viewer, tuple(setting_scales))  # type: ignore
        self._selected_layer = None


@_axis_metadata_component
class AxisUnits:
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel

    _axis_name_labels_tuple: tuple[QLabel, ...]
    _type_combobox_tuple: tuple[QComboBox, ...]
    _unit_combobox_tuple: tuple[QComboBox, ...]
    _unit_line_edit_tuple: tuple[QLineEdit, ...]
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
            active_layer = resolve_layer(self._napari_viewer)  # type: ignore

        if active_layer != self._selected_layer or active_layer is None:
            self._reset_tuples()
            self._create_tuples(active_layer)
            return

        layer_units = get_axes_units(self._napari_viewer, active_layer)  # type: ignore
        for i in range(len(layer_units)):
            with QSignalBlocker(self._unit_combobox_tuple[i]):
                # remove all items from the combobox
                self._unit_combobox_tuple[i].clear()
                unit_str = str(layer_units[i])
                matched_type: AxisUnitEnum = AxisUnitEnum.STRING
                for at in AxisUnitEnum:
                    unit_cfg = at.value
                    if unit_cfg is not None and unit_str in unit_cfg.units:
                        matched_type = at
                        break
                matched_cfg = matched_type.value
                if matched_cfg is not None:
                    self._unit_combobox_tuple[i].addItems(matched_cfg.units)
                    self._unit_combobox_tuple[i].setCurrentIndex(
                        self._unit_combobox_tuple[i].findText(unit_str)
                    )
                else:
                    for at in AxisUnitEnum:
                        unit_cfg = at.value
                        if unit_cfg is not None:
                            self._unit_combobox_tuple[i].addItems(
                                unit_cfg.units
                            )
                    self._unit_combobox_tuple[i].setCurrentIndex(
                        self._unit_combobox_tuple[i].findText(
                            AxisUnitEnum.SPACE.value.default
                        )
                    )
                with QSignalBlocker(self._type_combobox_tuple[i]):
                    self._type_combobox_tuple[i].setCurrentIndex(
                        self._type_combobox_tuple[i].findText(
                            str(matched_type)
                        )
                    )
            self._update_unit_line_edits_texts()
            self._update_units_visibilities()

    def get_entries_dict(
        self,
    ) -> dict[
        int,
        dict[
            str, tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None]
        ],
    ]:
        returning_dict: dict[
            int,
            dict[
                str,
                tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None],
            ],
        ] = {}
        for i in range(len(self._axis_name_labels_tuple)):
            returning_dict[i] = {}
            returning_dict[i]['axis_name_label'] = (
                [self._axis_name_labels_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['type_combobox'] = (
                [self._type_combobox_tuple[i]],
                1,
                1,
                '_on_type_combobox_changed',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['unit_combobox'] = (
                [self._unit_combobox_tuple[i], self._unit_line_edit_tuple[i]],
                1,
                1,
                '_on_unit_combobox_changed',
                Qt.AlignmentFlag.AlignVCenter,
            )
            returning_dict[i]['inherit_checkbox'] = (
                [self._inherit_checkbox_tuple[i]],
                1,
                1,
                '',
                Qt.AlignmentFlag.AlignVCenter,
            )
        return returning_dict

    def _reset_tuples(self) -> None: ...

    def _create_tuples(self, layer: 'Layer | None') -> None:
        if layer is None or layer == self._selected_layer:
            return
        layer_dimensions: int = get_layer_dimensions(layer)
        if layer_dimensions == 0:
            return
        setting_name_tuple: tuple[QLabel, ...] = _get_axis_label_tuple(
            self._napari_viewer, layer
        )
        setting_type_combobox_tuple: tuple[QComboBox, ...] = ()
        setting_unit_combobox_tuple: tuple[QComboBox, ...] = ()
        setting_unit_line_edit_tuple: tuple[QLineEdit, ...] = ()
        setting_inherit_checkbox_tuple: tuple[QCheckBox, ...] = (
            _get_checkbox_tuple(layer)
        )
        layer_units: tuple[pint.Unit | None, ...] = get_axes_units(
            self._napari_viewer, layer
        )
        for i in range(layer_dimensions):
            setting_unit_string: str = str(layer_units[i])
            setting_type_combobox: QComboBox = QComboBox()
            setting_unit_combobox: QComboBox = QComboBox()
            setting_unit_line_edit: QLineEdit = QLineEdit()
            for axis_type in AxisUnitEnum:
                setting_type_combobox.addItem(str(axis_type), axis_type)
            setting_axis_type: AxisUnitEnum | None = self._set_unit_combobox(
                setting_unit_string, setting_unit_combobox
            )
            if setting_axis_type is None:
                setting_index = setting_type_combobox.findData(
                    AxisUnitEnum.STRING
                )
            else:
                setting_index = setting_type_combobox.findData(
                    setting_axis_type
                )
            setting_type_combobox.setCurrentIndex(setting_index)
            setting_type_combobox_tuple += (setting_type_combobox,)
            setting_unit_combobox_tuple += (setting_unit_combobox,)
            setting_unit_line_edit_tuple += (setting_unit_line_edit,)
        self._axis_name_labels_tuple = setting_name_tuple
        self._type_combobox_tuple = setting_type_combobox_tuple
        self._unit_combobox_tuple = setting_unit_combobox_tuple
        self._unit_line_edit_tuple = setting_unit_line_edit_tuple
        self._inherit_checkbox_tuple = setting_inherit_checkbox_tuple
        self._selected_layer = layer

        for type_combobox in self._type_combobox_tuple:
            type_combobox.currentIndexChanged.connect(
                self._on_type_combobox_changed
            )
        for unit_combobox in self._unit_combobox_tuple:
            unit_combobox.currentIndexChanged.connect(
                self._on_unit_combobox_changed
            )
        for line_edit in self._unit_line_edit_tuple:
            line_edit.editingFinished.connect(self._on_unit_combobox_changed)

        self._update_units_visibilities()
        self._update_unit_line_edits_texts()

    def _update_units_visibilities(self) -> None:
        number_of_axis: int = len(self._axis_name_labels_tuple)
        for axis_index in range(number_of_axis):
            type_combobox: QComboBox = self._type_combobox_tuple[axis_index]
            unit_combobox: QComboBox = self._unit_combobox_tuple[axis_index]
            unit_line_edit: QLineEdit = self._unit_line_edit_tuple[axis_index]
            axis_type: AxisUnitEnum | None = type_combobox.currentData()
            if axis_type is None:
                unit_combobox.setVisible(False)
                unit_line_edit.setVisible(True)
            if axis_type == AxisUnitEnum.STRING:
                unit_combobox.setVisible(False)
                unit_line_edit.setVisible(True)
            else:
                unit_combobox.setVisible(True)
                unit_line_edit.setVisible(False)

    def _set_unit_combobox(
        self, unit_type_string: str | None, combobox: QComboBox
    ) -> AxisUnitEnum | None:
        with QSignalBlocker(combobox):
            combobox.clear()
        combined_pint_units_list: list[pint.Unit] = []
        found_type: AxisUnitEnum | None = None
        for axis_type in AxisUnitEnum:
            unit_cfg = axis_type.value
            if unit_cfg is None:
                continue
            combined_pint_units_list.extend(unit_cfg.pint_units())
            if (
                unit_type_string is not None
                and unit_type_string in unit_cfg.units
            ):
                found_type = axis_type
        if found_type is not None:
            chosen_cfg = found_type.value
            if chosen_cfg is None:
                return AxisUnitEnum.STRING
            pint_units = chosen_cfg.pint_units()
        else:
            pint_units = combined_pint_units_list
        applicatin_reg: pint.registry.ApplicationRegistry = (
            pint.get_application_registry()
        )
        with QSignalBlocker(combobox):
            for pint_unit in pint_units:
                combobox.addItem(str(pint_unit), pint_unit)
            if found_type is None:
                combobox.setCurrentIndex(0)
            else:
                setting_pint_unit: pint.Unit = applicatin_reg.Unit(
                    unit_type_string
                )
                index: int = combobox.findText(str(setting_pint_unit))
                combobox.setCurrentIndex(index)
        return found_type

    def _set_axis_name_labels(self) -> None: ...

    def _set_checkboxes_visibility(self, visible: bool) -> None:
        _ = visible

    def _set_current_combobox_units_to_layer(self) -> None:
        units_list: list[str] = []
        number_of_axis: int = len(self._axis_name_labels_tuple)
        for axis_index in range(number_of_axis):
            type_combobox: QComboBox = self._type_combobox_tuple[axis_index]
            unit_combobox: QComboBox = self._unit_combobox_tuple[axis_index]
            unit_line_edit: QLineEdit = self._unit_line_edit_tuple[axis_index]
            axis_type: AxisUnitEnum | None = type_combobox.currentData()
            pint_unit_text: str | None = None
            if axis_type is None:
                pint_unit_text = None
                units_list.append(None)  # type: ignore
                continue
            elif axis_type == AxisUnitEnum.STRING:
                line_edit_text: str = unit_line_edit.text()
                if line_edit_text.strip().lower() == 'none':
                    units_list.append(None)  # type: ignore
                    continue
                units_list.append(line_edit_text)
                continue
            pint_unit_text = unit_combobox.currentText().strip()
            if pint_unit_text.strip().lower() == 'none':
                units_list.append(None)  # type: ignore
                continue
            units_list.append(pint_unit_text)
        try:
            set_axes_units(self._napari_viewer, tuple(units_list))
        except (AttributeError, ValueError):
            show_error(
                f'The layer units {units_list} has no pint.Unit equivalents'
            )
        self._update_unit_line_edits_texts()

    def _on_type_combobox_changed(self) -> None:
        number_of_axis: int = len(self._axis_name_labels_tuple)
        current_units: tuple[pint.Unit | None, ...] = get_axes_units(
            self._napari_viewer, resolve_layer(self._napari_viewer)
        )
        for axis_number in range(number_of_axis):
            type_combobox: QComboBox = self._type_combobox_tuple[axis_number]
            unit_combobox: QComboBox = self._unit_combobox_tuple[axis_number]
            current_unit = str(current_units[axis_number])
            axis_type = type_combobox.currentData()
            if not isinstance(axis_type, AxisUnitEnum):
                continue
            unit_cfg = axis_type.value
            with QSignalBlocker(unit_combobox):
                unit_combobox.clear()
                if unit_cfg is not None:
                    for unit in unit_cfg.pint_units():
                        unit_combobox.addItem(str(unit), unit)
                setting_index: int = unit_combobox.findText(current_unit)
                if setting_index == -1 and unit_cfg is not None:
                    setting_index = unit_combobox.findText(unit_cfg.default)
                unit_combobox.setCurrentIndex(setting_index)
        self._set_current_combobox_units_to_layer()
        self._update_units_visibilities()

    def _update_unit_line_edits_texts(self) -> None:
        current_units = get_axes_units(
            self._napari_viewer, resolve_layer(self._napari_viewer)
        )
        number_of_axis: int = len(self._axis_name_labels_tuple)
        for axis_index in range(number_of_axis):
            unit_line_edit = self._unit_line_edit_tuple[axis_index]
            with QSignalBlocker(unit_line_edit):
                unit_line_edit.setText(str(current_units[axis_index]))

    def _on_unit_combobox_changed(self) -> None:
        self._set_current_combobox_units_to_layer()
        self._update_units_visibilities()
        return

    def inherit_layer_properties(self, template_layer: 'Layer') -> None:
        current_layer: Layer | None = resolve_layer(self._napari_viewer)
        if current_layer is None:
            return
        self._set_axis_name_labels()
        current_layer_units: tuple[pint.Unit | None, ...] = get_axes_units(
            self._napari_viewer, current_layer
        )
        template_units: tuple[pint.Unit | None, ...] = get_axes_units(
            self._napari_viewer, template_layer
        )
        setting_units: list[pint.Unit | None] = []
        checkbox_list: tuple[QCheckBox, ...] = self._inherit_checkbox_tuple
        for i in range(len(checkbox_list)):
            if checkbox_list[i].isChecked():
                setting_units.append(template_units[i])
            else:
                setting_units.append(current_layer_units[i])
        set_axes_units(self._napari_viewer, tuple(setting_units))  # type: ignore


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


class AxisMetadata:
    """This is the class that integrates all of the axis metadata components together and instantiates them. This class itself
    is instantiated in the MetadataWidgetAPI class, which is ultimately the main class passed to napari. This class will only hold the
    components instances and everything else is handled in the MetadataWidgetAPI class or the individual metadata component classes."""

    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _axis_metadata_components_dict: dict[str, AxisComponent]

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None:
        self._napari_viewer = napari_viewer
        self._main_widget = main_widget
        self._axis_metadata_components_dict: dict[str, AxisComponent] = {}

        for (
            metadata_comp_name,
            metadata_component_class,
        ) in AXIS_METADATA_COMPONENTS_DICT.items():
            self._axis_metadata_components_dict[metadata_comp_name] = (
                metadata_component_class(napari_viewer, main_widget)
            )

        self._set_inheritance_checkbox_visibility(False)

    def _update_axes_labels(self) -> None:
        for axis_component in self._axis_metadata_components_dict.values():
            cast_component: AxisComponent = cast(AxisComponent, axis_component)
            cast_component._set_axis_name_labels()

    def _set_inheritance_checkbox_visibility(self, visible: bool) -> None:
        for axis_component in self._axis_metadata_components_dict.values():
            cast_component: AxisComponent = cast(AxisComponent, axis_component)
            cast_component._set_checkboxes_visibility(visible)
