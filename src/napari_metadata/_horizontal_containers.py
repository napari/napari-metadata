from qtpy.QtWidgets import (
    QPushButton,
    QScrollArea,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QWheelEvent


class HorizontalSectionContainer(QWidget):
    def __init__(self, viewer: 'napari.viewer.Viewer'):
        super().__init__()
        self._viewer = viewer
        self._set_text = ' '

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(4)

        self._button = RotatedButton(' ')
        font = self._button.font()
        font.setBold(True)
        self._button.setFont(font)
        self._button.setCheckable(True)
        self._button.toggled.connect(self._expanding_area_set_visible)
        self._layout.addWidget(self._button, 0)

        self._expanding_area = QScrollArea()
        self._expanding_area.setWidgetResizable(True)
        self._expanding_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._expanding_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._expanding_area.setVisible(False)
        self._expanding_area.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Expanding
        )
        self._layout.addWidget(self._expanding_area, 1)

        self._expanding_area.setFixedWidth(0)

    def _expanding_area_set_visible(self, checked: bool) -> None:
        self._expanding_area.setVisible(checked)
        self._sync_body_width()
        if not checked:
            self._button.setText('▶ ' + self._set_text)
        else:
            self._button.setText('▼ ' + self._set_text)

        self._expanding_area.updateGeometry()
        self.updateGeometry()

    def _sync_body_width(self) -> None:
        current_widget = self._expanding_area.widget()
        if (not self._expanding_area.isVisible()) or current_widget is None:
            self._expanding_area.setFixedWidth(0)
            return

        widget_width = current_widget.sizeHint().width()

        scroll_bar_width = (
            self._expanding_area.verticalScrollBar().sizeHint().width()
        )

        frame = 2 * self._expanding_area.frameWidth()

        self._expanding_area.setFixedWidth(
            widget_width + scroll_bar_width + frame
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

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        wrapper_layout.addWidget(setting_widget)
        wrapper_layout.addStretch(1)

        self._expanding_area.setWidget(wrapper)
        self._sync_body_width()

    def _set_button_text(self, button_text: str) -> None:
        self._set_text = button_text
        self._expanding_area_set_visible(False)

    def expandedWidth(self) -> int:
        current_widget = self._expanding_area.widget()
        if (not self.isExpanded()) or current_widget is None:
            return 0
        return max(1, current_widget.sizeHint().width())


class RotatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def paintEvent(self, a0):
        painter = QStylePainter(self)

        painter.rotate(-90)
        painter.translate(-self.height(), 0)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        opt.rect = opt.rect.transposed()

        painter.drawControl(QStyle.ControlElement.CE_PushButton, opt)

    def sizeHint(self):
        size = super().sizeHint()
        return QSize(size.height(), size.width())

    def minimumSizeHint(self):
        return self.sizeHint()


class HorizontalOnlyOuterScrollArea(QScrollArea):
    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        w = self.widget()
        if w is not None:
            w.setFixedHeight(self.viewport().height())

    def wheelEvent(self, a0: QWheelEvent | None):
        a0.ignore()
