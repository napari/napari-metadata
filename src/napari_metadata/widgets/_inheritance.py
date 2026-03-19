from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from qtpy.QtCore import QSignalBlocker, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.layers import Layer
    from napari.utils.events import SelectableEventedList

BLOCKS_SPACING = 20


class InheritanceWidget(QWidget):
    def __init__(
        self,
        layers: SelectableEventedList[Layer],
        *,
        on_apply_inheritance: Callable[[Layer], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._layers = layers
        self._template_layer: Layer | None = None
        self._inheriting_layer: Layer | None = None
        self._on_apply_inheritance = on_apply_inheritance
        self._event_connected_layer: Layer | None = None

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)

        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
        )

        self._template_layer_label = QLabel('Copy from template layer')
        self._template_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_layer_label.setStyleSheet('font-weight: bold;')

        self._template_combobox: QComboBox = QComboBox()
        self._template_combobox.currentIndexChanged.connect(
            self._on_combobox_selection_changed
        )

        self._inheriting_layer_label: QLabel = QLabel('Copy to layer')
        self._inheriting_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._inheriting_layer_label.setStyleSheet('font-weight: bold')

        self._inheriting_layer_name: QLabel = QLabel('None selected')

        self._different_dims_label: QLabel = QLabel(
            'Layers dimensions do not match'
        )
        self._different_dims_label.setStyleSheet(
            'color: red; font-weight: bold;'
        )
        self._different_dims_label.setVisible(False)

        self._apply_button = QPushButton('Apply checked metadata')
        self._apply_button.pressed.connect(self._on_apply_button_pressed)

        self._layout.addWidget(self._template_layer_label)
        self._layout.addWidget(self._template_combobox)
        self._layout.addSpacing(BLOCKS_SPACING)
        self._layout.addWidget(self._inheriting_layer_label)
        self._layout.addWidget(self._inheriting_layer_name)
        self._layout.addSpacing(BLOCKS_SPACING)
        self._layout.addWidget(self._different_dims_label)
        self._layout.addWidget(self._apply_button)
        self._layout.addStretch(1)

        # Wire layer list events directly
        self._layers.events.inserted.connect(self._update_layers_combobox)
        self._layers.events.removed.connect(self._update_layers_combobox)
        self._layers.events.changed.connect(self._update_layers_combobox)

        self._layers.selection.events.active.connect(
            self._update_inheriting_label
        )
        self._layers.selection.events.active.connect(
            self._on_layer_selection_changed
        )

        self._update_layers_combobox()
        self._update_inheriting_label()

    def _update_layers_combobox(self) -> None:
        layers_list: list[Layer] = list(self._layers)
        with QSignalBlocker(self._template_combobox):
            self._template_combobox.clear()
        if not len(layers_list):
            self._template_layer = None
            return
        with QSignalBlocker(self._template_combobox):
            self._template_combobox.addItem('None', userData=None)
            for setting_layer in layers_list:
                self._template_combobox.addItem(
                    setting_layer.name, userData=setting_layer
                )
            idx = self._template_combobox.findData(
                self._template_layer, Qt.ItemDataRole.UserRole
            )
            if idx == -1:
                self._template_layer = None
                idx = self._template_combobox.findData(
                    None, Qt.ItemDataRole.UserRole
                )
            self._template_combobox.setCurrentIndex(idx)

    def _update_inheriting_label(self) -> None:
        active_layer: Layer | None = self._layers.selection.active
        if active_layer is None:
            self._inheriting_layer_name.setText('None selected')
            self._inheriting_layer = None
            self._compare_template_and_inheriting_layers()
            return
        self._inheriting_layer_name.setText(active_layer.name)
        self._inheriting_layer = active_layer
        self._compare_template_and_inheriting_layers()

    def _compare_template_and_inheriting_layers(self) -> None:
        if (
            self._inheriting_layer is self._template_layer
            or self._template_layer is None
            or self._inheriting_layer is None
        ):
            self._apply_button.setEnabled(False)
            self._different_dims_label.setVisible(False)
        else:
            if self._template_layer.ndim != self._inheriting_layer.ndim:
                self._apply_button.setEnabled(False)
                self._different_dims_label.setVisible(True)
            else:
                self._apply_button.setEnabled(True)
                self._different_dims_label.setVisible(False)

    def _on_apply_button_pressed(self) -> None:
        template_layer = self._template_layer
        if template_layer is None:
            return
        inheriting_layer = self._inheriting_layer
        if inheriting_layer is None:
            return
        if (
            template_layer is inheriting_layer
            or template_layer.ndim != inheriting_layer.ndim
        ):
            return
        if self._on_apply_inheritance is not None:
            self._on_apply_inheritance(template_layer)

    def _on_combobox_selection_changed(self) -> None:
        selected_item: Layer | None = self._template_combobox.currentData(
            Qt.ItemDataRole.UserRole
        )
        self._template_layer = selected_item
        self._compare_template_and_inheriting_layers()

    def _on_layer_name_changed(self) -> None:
        self._update_layers_combobox()
        self._update_inheriting_label()

    def _on_layer_selection_changed(self) -> None:
        current_layer = self._layers.selection.active
        if current_layer is self._event_connected_layer:
            return
        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError):
                self._event_connected_layer.events.name.disconnect(
                    self._on_layer_name_changed
                )
        self._event_connected_layer = current_layer
        if current_layer is not None:
            current_layer.events.name.connect(self._on_layer_name_changed)

    def closeEvent(self, a0):
        with suppress(TypeError, ValueError):
            self._layers.events.inserted.disconnect(
                self._update_layers_combobox
            )
        with suppress(TypeError, ValueError):
            self._layers.events.removed.disconnect(
                self._update_layers_combobox
            )
        with suppress(TypeError, ValueError):
            self._layers.events.changed.disconnect(
                self._update_layers_combobox
            )
        with suppress(TypeError, ValueError):
            self._layers.selection.events.active.disconnect(
                self._update_inheriting_label
            )
        with suppress(TypeError, ValueError):
            self._layers.selection.events.active.disconnect(
                self._on_layer_selection_changed
            )
        if self._event_connected_layer is not None:
            with suppress(TypeError, ValueError):
                self._event_connected_layer.events.name.disconnect(
                    self._on_layer_name_changed
                )
        super().closeEvent(a0)
