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

from napari_metadata.layer_utils import (
    connect_callback_to_layer_name_changed,
    connect_callback_to_layer_selection_events,
    connect_callback_to_list_events,
    disconnect_callback_to_layer_name_changed,
    disconnect_callback_to_layer_selection_events,
    disconnect_callback_to_list_events,
    get_layers_list,
    resolve_layer,
)
from napari_metadata.widgets._protocols import MetadataWidgetAPI

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer

BLOCKS_SPACING = 20


class InheritanceWidget(QWidget):
    def __init__(
        self,
        napari_viewer: 'ViewerModel',
        metadata_widget: MetadataWidgetAPI,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._napari_viewer = napari_viewer
        self._template_layer: Layer | None = None
        self._inheriting_layer: Layer | None = None
        self._metadata_widget: MetadataWidgetAPI = metadata_widget
        self._selected_layer: Layer | None = None

        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)

        self.setMinimumWidth(300)

        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        )

        self._template_layer_label = QLabel('Template layer')
        self._template_layer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_layer_label.setStyleSheet('font-weight: bold;')

        self._template_combobox: QComboBox = QComboBox()
        self._template_combobox.currentIndexChanged.connect(
            self._on_combobox_selection_changed
        )

        self._inheriting_layer_label: QLabel = QLabel('Inheriting layer')
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

        self._update_layers_combobox_callback = self._update_layers_combobox
        connect_callback_to_list_events(
            self._napari_viewer, self._update_layers_combobox_callback
        )

        self._update_inheriting_layer_callback = self._update_inheriting_label
        connect_callback_to_layer_selection_events(
            self._napari_viewer, self._update_inheriting_layer_callback
        )

        self._layer_selection_changed_callback = (
            self._on_layer_selection_changed
        )
        self._layer_name_changed_callback = self._on_layer_name_changed
        connect_callback_to_layer_selection_events(
            self._napari_viewer, self._layer_selection_changed_callback
        )

        self._update_layers_combobox()
        self._update_inheriting_label()

    def _update_layers_combobox(self) -> None:
        layers_list: list[Layer] = get_layers_list(self._napari_viewer)
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
            if (
                not self._template_combobox.findData(
                    self._template_layer, Qt.ItemDataRole.UserRole
                )
                or self._template_combobox.findData(
                    self._template_layer, Qt.ItemDataRole.UserRole
                )
                == -1
            ):
                self._template_layer = None
                self._template_combobox.setCurrentIndex(
                    self._template_combobox.findData(
                        None, Qt.ItemDataRole.UserRole
                    )
                )
                return
            self._template_combobox.setCurrentIndex(
                self._template_combobox.findData(
                    self._template_layer, Qt.ItemDataRole.UserRole
                )
            )

    def _update_inheriting_label(self) -> None:
        active_layer: Layer | None = resolve_layer(self._napari_viewer, None)
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
        self._metadata_widget.apply_inheritance_to_current_layer(
            template_layer
        )

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
        current_layer = resolve_layer(self._napari_viewer)
        if current_layer is self._selected_layer:
            return
        if self._selected_layer is not None:
            disconnect_callback_to_layer_name_changed(
                self._napari_viewer,
                self._layer_name_changed_callback,
                self._selected_layer,
            )
        self._selected_layer = current_layer
        if current_layer is not None:
            connect_callback_to_layer_name_changed(
                self._napari_viewer,
                self._layer_name_changed_callback,
                current_layer,
            )

    def closeEvent(self, a0):
        disconnect_callback_to_list_events(
            self._napari_viewer, self._update_layers_combobox_callback
        )
        disconnect_callback_to_layer_selection_events(
            self._napari_viewer, self._update_inheriting_layer_callback
        )
        super().closeEvent(a0)
