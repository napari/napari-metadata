from qtpy.QtWidgets import (
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from qtpy.QtCore import Qt, QObject, QEvent


class VerticalSectionContainer(QWidget):
    def __init__(self, viewer: 'napari.viewer.Viewer'):
        super().__init__()
        self._viewer = viewer
        self._set_text = ' '

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(4)

        self._button = QPushButton(' ')
        font = self._button.font()
        font.setBold(True)
        self._button.setFont(font)
        self._button.setCheckable(True)
        self._button.toggled.connect(self._expanding_area_set_visible)
        self._layout.addWidget(self._button, 0)

        self._expanding_area = QScrollArea()
        self._expanding_area.setWidgetResizable(True)
        self._expanding_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._expanding_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.disable_horizontal_scrolling_wheel_filter = (
            DisableWheelScrollingFilter()
        )
        self._expanding_area.horizontalScrollBar().installEventFilter(
            self.disable_horizontal_scrolling_wheel_filter
        )
        self._expanding_area.setVisible(False)
        self._expanding_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self._layout.addWidget(self._expanding_area, 0)

    def _expanding_area_set_visible(self, checked: bool) -> None:
        self._expanding_area.setVisible(checked)
        self._sync_body_height()
        if not checked:
            self._button.setText('▶ ' + self._set_text)
        else:
            self._button.setText('▼ ' + self._set_text)

    def _sync_body_height(self) -> None:
        current_widget = self._expanding_area.widget()
        if (not self._expanding_area.isVisible()) or current_widget is None:
            self._expanding_area.setFixedHeight(0)
            return

        widget_height = current_widget.sizeHint().height()

        scroll_bar_height = (
            self._expanding_area.horizontalScrollBar().sizeHint().height()
        )

        frame = 2 * self._expanding_area.frameWidth()

        self._expanding_area.setFixedHeight(
            widget_height + scroll_bar_height + frame
        )

        current_widget.updateGeometry()
        self._expanding_area.updateGeometry()
        self.updateGeometry()

    def isExpanded(self) -> bool:
        return self._button.isChecked()

    def onToggled(self, callback) -> None:
        self._button.toggled.connect(callback)

    def _set_expanding_area_widget(self, setting_widget: QWidget) -> None:
        old = self._expanding_area.takeWidget()
        if old is not None:
            old.deleteLater()

        setting_widget.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Preferred
        )

        self._expanding_area.setWidget(setting_widget)
        self._sync_body_height()

    def _set_button_text(self, button_text: str) -> None:
        self._set_text = button_text
        self._expanding_area_set_visible(False)

    def expandedHeight(self) -> int:
        current_widget = self._expanding_area.widget()
        if (not self.isExpanded()) or current_widget is None:
            return 0
        return max(1, current_widget.sizeHint().height())


class DisableWheelScrollingFilter(QObject):
    def eventFilter(self, a0, a1):
        if a1.type() == QEvent.Wheel:
            return True
        return False
