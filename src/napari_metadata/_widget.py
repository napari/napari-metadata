from collections.abc import Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Optional

from qtpy.QtCore import Qt
from qtpy.QtGui import QShowEvent
from qtpy.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from napari_metadata._axes_widget import AxesWidget, ReadOnlyAxesWidget
from napari_metadata._file_size import generate_display_size
from napari_metadata._model import (
    coerce_extra_metadata,
    is_metadata_equal_to_original,
)
from napari_metadata._space_units import SpaceUnits
from napari_metadata._spatial_units_combo_box import SpatialUnitsComboBox
from napari_metadata._time_units import TimeUnits
from napari_metadata._transform_widget import (
    ReadOnlyTransformWidget,
    TransformWidget,
)
from napari_metadata._widget_utils import readonly_lineedit

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


class EditableMetadataWidget(QWidget):
    def __init__(self, viewer: 'ViewerModel') -> None:
        super().__init__()
        self._viewer = viewer
        self._selected_layer = None
        layout = QVBoxLayout()
        self.setLayout(layout)

        self._attribute_widget = QWidget()
        layout.addWidget(self._attribute_widget)

        self._attribute_layout = QGridLayout()
        self._attribute_layout.setContentsMargins(0, 0, 0, 0)
        self._attribute_widget.setLayout(self._attribute_layout)

        self.name = QLineEdit()
        self._add_attribute_row('Layer name', self.name)
        self.name.textChanged.connect(self._on_name_changed)

        self._axes_widget = AxesWidget(viewer)
        self._add_attribute_row('Axes', self._axes_widget)

        self._spacing_widget = TransformWidget(viewer)
        self._add_attribute_row('Transforms', self._spacing_widget)

        self._spatial_units = SpatialUnitsComboBox(viewer)
        self._spatial_units.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._add_attribute_row('Space units', self._spatial_units)
        self._spatial_units.currentTextChanged.connect(
            self._on_spatial_units_changed
        )

        self._temporal_units = QComboBox()
        self._temporal_units.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._temporal_units.addItems(TimeUnits.names())
        self._add_attribute_row('Time units', self._temporal_units)
        self._temporal_units.currentTextChanged.connect(
            self._on_temporal_units_changed
        )

        restore_layout = QHBoxLayout()
        restore_layout.addStretch(1)
        self._restore_defaults = QPushButton('Restore defaults')
        self._restore_defaults.setStyleSheet(
            'QPushButton {'
            'color: #898D93;'
            'background: transparent;'
            '}'
            'QPushButton::enabled {'
            'color: #66C1FF;'
            '}'
        )
        self._restore_defaults.clicked.connect(self._on_restore_clicked)
        restore_layout.addWidget(self._restore_defaults)
        layout.addLayout(restore_layout)

        # Push control widget to bottom.
        layout.addStretch(1)

        self._control_widget = QWidget()
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        self._control_widget.setLayout(control_layout)

        self.show_readonly = QPushButton('View full metadata')
        self.show_readonly.setStyleSheet(
            'QPushButton {color: #66C1FF;background: transparent;}'
        )

        control_layout.addWidget(self.show_readonly)
        control_layout.addStretch(1)
        self.cancel_button = QPushButton('Cancel')
        control_layout.addWidget(self.cancel_button)
        self._save_button = QPushButton('Save')
        self._save_button.setEnabled(False)
        control_layout.addWidget(self._save_button)

        layout.addWidget(self._control_widget)

        self._viewer.dims.events.axis_labels.connect(
            self._update_restore_enabled
        )

    def set_selected_layer(self, layer: Optional['Layer']) -> None:
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


class ReadOnlyMetadataWidget(QWidget):
    def __init__(self, viewer: 'ViewerModel') -> None:
        super().__init__()
        self._viewer = viewer
        self._selected_layer = None
        layout = QVBoxLayout()
        self.setLayout(layout)

        self._attribute_widget = QWidget()
        layout.addWidget(self._attribute_widget)

        self._attribute_layout = QGridLayout()
        self._attribute_layout.setContentsMargins(0, 0, 0, 0)
        self._attribute_widget.setLayout(self._attribute_layout)

        item_label = QLabel('Item')
        item_label.setStyleSheet('font-weight: bold')
        self._attribute_layout.addWidget(item_label, 0, 0)
        value_label = QLabel('Value')
        value_label.setStyleSheet('font-weight: bold')
        self._attribute_layout.addWidget(value_label, 0, 1)

        self.name = self._add_attribute_row('Layer name')
        self.file_path = self._add_attribute_row('File name')
        self.plugin = self._add_attribute_row('Plugin')
        self.data_shape = self._add_attribute_row('Array shape')
        self.data_type = self._add_attribute_row('Data type')
        self.file_size = self._add_attribute_row('File size')

        self._axes_widget = ReadOnlyAxesWidget(viewer)
        self._add_attribute_row('Axes', self._axes_widget)

        self._spacing_widget = ReadOnlyTransformWidget(viewer)
        self._add_attribute_row('Transforms', self._spacing_widget)

        self.spatial_units = self._add_attribute_row('Space units')
        self.temporal_units = self._add_attribute_row('Time units')

        # Push control widget to bottom.
        layout.addStretch(1)

        self._control_widget = QWidget()
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        self._control_widget.setLayout(control_layout)

        self.show_editable = QPushButton('View editable metadata')
        self.show_editable.setStyleSheet(
            'QPushButton {color: #66C1FF;background: transparent;}'
        )

        control_layout.addWidget(self.show_editable)
        control_layout.addStretch(1)
        self.close_button = QPushButton('Close')
        control_layout.addWidget(self.close_button)

        layout.addWidget(self._control_widget)

    def set_selected_layer(self, layer: Optional['Layer']) -> None:
        if layer == self._selected_layer:
            return

        if self._selected_layer is not None:
            self._selected_layer.events.name.disconnect(
                self._on_selected_layer_name_changed
            )
            self._selected_layer.events.data.disconnect(
                self._on_selected_layer_data_changed
            )

        if layer is not None:
            self.name.setText(layer.name)
            self.file_path.setText(str(layer.source.path))
            self.plugin.setText(_layer_plugin_info(layer))
            self.data_shape.setText(_layer_data_shape(layer))
            self.data_type.setText(_layer_data_dtype(layer))
            extras = coerce_extra_metadata(self._viewer, layer)
            self.spatial_units.setText(str(extras.get_space_unit()))
            self.temporal_units.setText(str(extras.get_time_unit()))
            self.file_size.setText(generate_display_size(layer))

            layer.events.name.connect(self._on_selected_layer_name_changed)
            layer.events.data.connect(self._on_selected_layer_data_changed)

            self._axes_widget.set_selected_layer(layer)

        self._spacing_widget.set_selected_layer(layer)

        self._selected_layer = layer

    def set_spatial_units(self, units: str) -> None:
        self.spatial_units.setText(units)

    def set_temporal_units(self, units: str) -> None:
        self.temporal_units.setText(units)

    def _add_attribute_row(
        self, name: str, widget: Optional[QWidget] = None
    ) -> QWidget:
        if widget is None:
            widget = readonly_lineedit()
        layout = self._attribute_widget.layout()
        row = layout.rowCount()
        label = QLabel(name)
        label.setBuddy(widget)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)
        return widget

    def _on_selected_layer_name_changed(self, event) -> None:
        self.name.setText(event.source.name)

    def _on_selected_layer_data_changed(self) -> None:
        assert (layer := self._selected_layer)
        self.data_shape.setText(_layer_data_shape(layer))
        self.data_type.setText(_layer_data_dtype(layer))


class InfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        info_label = QLabel('Select a single layer to view its metadata')
        layout.addWidget(info_label)
        layout.addStretch(1)
        self.setLayout(layout)


class MetadataWidget(QStackedWidget):
    def __init__(self, napari_viewer: 'ViewerModel'):
        super().__init__()
        self._viewer = napari_viewer
        self._selected_layer = None

        self._info_widget = InfoWidget()
        self.addWidget(self._info_widget)

        self._editable_widget = EditableMetadataWidget(napari_viewer)
        self._editable_widget.show_readonly.clicked.connect(
            self._show_readonly
        )
        self._editable_widget.cancel_button.clicked.connect(
            self._remove_dock_widget
        )
        self.addWidget(self._editable_widget)

        self._readonly_widget = ReadOnlyMetadataWidget(napari_viewer)
        self._readonly_widget.show_editable.clicked.connect(
            self._show_editable
        )
        self._readonly_widget.close_button.clicked.connect(
            self._remove_dock_widget
        )
        self.addWidget(self._readonly_widget)

        self._editable_widget._spatial_units.currentTextChanged.connect(
            self._readonly_widget.set_spatial_units
        )
        self._editable_widget._temporal_units.currentTextChanged.connect(
            self._readonly_widget.set_temporal_units
        )

        self._viewer.layers.selection.events.changed.connect(
            self._on_selected_layers_changed
        )

        self._on_selected_layers_changed()

    def showEvent(self, event: QShowEvent) -> None:
        self._viewer.axes.colored = False
        self._viewer.axes.visible = True
        self._viewer.scale_bar.visible = True
        return super().showEvent(event)

    def _show_readonly(self) -> None:
        self.setCurrentWidget(self._readonly_widget)

    def _show_editable(self) -> None:
        self.setCurrentWidget(self._editable_widget)

    def _on_selected_layers_changed(self) -> None:
        layer = None
        if len(self._viewer.layers.selection) == 1:
            layer = next(iter(self._viewer.layers.selection))

        if layer is None:
            self.setCurrentWidget(self._info_widget)
        else:
            self.setCurrentWidget(self._editable_widget)

        # This can occur when there is no selected layer at initialization,
        # so do some things must be done before this.
        if layer == self._selected_layer:
            return

        if layer is not None:
            coerce_extra_metadata(self._viewer, layer)

        self._readonly_widget.set_selected_layer(layer)
        self._editable_widget.set_selected_layer(layer)

        self._selected_layer = layer

    def _remove_dock_widget(self) -> None:
        # To constrain our implementation and for testing, we only want
        # the type of _viewer to be ViewerModel and not Viewer.
        # This works around that typing information.
        if window := getattr(self._viewer, 'window', None):
            window.remove_dock_widget(self)


def _layer_plugin_info(layer: 'Layer') -> str:
    source = layer.source
    return (
        str(source.reader_plugin)
        if source.sample is None
        else str(source.sample)
    )


def _layer_data_shape(layer: 'Layer') -> str:
    data = layer.data
    if hasattr(data, 'shape'):
        return str(data.shape)
    if isinstance(data, Sequence):
        return f'{(len(data),)}'
    return 'Unknown'


def _layer_data_dtype(layer: 'Layer') -> str:
    data = layer.data
    if hasattr(data, 'dtype'):
        return str(data.dtype)
    if (
        isinstance(data, Sequence)
        and len(data) > 0
        and hasattr(data[0], 'dtype')
    ):
        return str(data[0].dtype)
    return 'Unknown'
