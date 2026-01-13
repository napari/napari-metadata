from qtpy.QtWidgets import (
    QPushButton,
    QScrollArea,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
)
from qtpy.QtCore import Qt, QSize


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
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._expanding_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._expanding_area.setVisible(False)
        self._expanding_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self._layout.addWidget(self._expanding_area, 0)

    def _expanding_area_set_visible(self, checked: bool) -> None:
        self._expanding_area.setVisible(checked)
        self._sync_body_width()
        if not checked:
            self._button.setText('▶ ' + self._set_text)
        else:
            self._button.setText('▼ ' + self._set_text)

    def _sync_body_width(self) -> None:
        current_widget = self._expanding_area.widget()
        if (not self._expanding_area.isVisible()) or current_widget is None:
            self._expanding_area.setFixedWidth(0)
            return

        widget_width = current_widget.sizeHint().width()

        scroll_bar_width = (
            self._expanding_area.horizontalScrollBar().sizeHint().width()
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

        setting_widget.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Preferred
        )

        self._expanding_area.setWidget(setting_widget)
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
        # Use QStylePainter to handle the complex drawing of the button body
        painter = QStylePainter(self)

        # Move and rotate the entire coordinate system
        # Since we rotate 90 degrees, we swap height and width logic
        painter.rotate(-90)
        painter.translate(-self.height(), 0)

        # Prepare the standard options for a button (hover, pressed, etc.)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        # Crucial: We must swap the rectangle coordinates to match the rotation
        # Otherwise, the button thinks it is drawing in the old horizontal space
        opt.rect = opt.rect.transposed()

        # Draw the button background and text using the current theme
        painter.drawControl(QStyle.ControlElement.CE_PushButton, opt)

    def sizeHint(self):
        # Swap width and height for the layout engine
        size = super().sizeHint()
        return QSize(size.height(), size.width())

    def minimumSizeHint(self):
        return self.sizeHint()
