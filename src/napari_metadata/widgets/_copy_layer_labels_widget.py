from napari.components import Dims, LayerList
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CopyLayerLabelsToAllWidget(QWidget):
    def __init__(
        self, layer_list: LayerList, viewer_dims: Dims, parent_widget: QWidget
    ) -> None:
        super().__init__(parent_widget)
        self.ll = layer_list
        self._parent_widget = parent_widget

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._copy_labels_title = QLabel('Copy layer labels to all layers')
        self._copy_labels_title.setStyleSheet('font-weight: bold')
        self._layout.addWidget(self._copy_labels_title)

        self._template_c = QWidget()
        self._template_c_layout = QHBoxLayout()
        self._template_c_layout.setContentsMargins(0, 0, 0, 0)
        self._template_c.setLayout(self._template_c_layout)
        self._layout.addWidget(self._template_c)

        self._template_layer_l = QLabel('Template layer name:')
        self._template_layer_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._template_layer_l.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_c_layout.addWidget(self._template_layer_l)

        self._layer_l = QLabel('')
        self._layer_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._layer_l.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._template_c_layout.addWidget(self._layer_l)

        self._template_c_layout.addStretch()

        self._all_layers_title_c = QWidget()
        self._all_layers_title_c_layout = QHBoxLayout()
        self._all_layers_title_c_layout.setContentsMargins(0, 0, 0, 0)
        self._all_layers_title_c.setLayout(self._all_layers_title_c_layout)
        self._layout.addWidget(self._all_layers_title_c)

        self._resulting_labels_title = QLabel('Resulting labels')
        self._resulting_labels_title.setStyleSheet('font-weight: bold')
        self._resulting_labels_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._resulting_labels_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._all_layers_title_c_layout.addWidget(self._resulting_labels_title)

        self._affected_layers_number_l = QLabel('Affected layers:')
        self._affected_layers_number_l.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._all_layers_title_c_layout.addWidget(
            self._affected_layers_number_l
        )

        self.ll.selection.events.active.connect(
            self._on_selected_layer_changed
        )
        self._on_selected_layer_changed()

    def _on_selected_layer_changed(self) -> None:
        """Update the template-layer display when active selection changes."""
        active_layer = self.ll.selection.active
        self._layer_l.setText(active_layer.name if active_layer else '')
