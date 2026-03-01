"""Unified collapsible section container supporting both vertical and horizontal orientations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtGui import QWheelEvent
from qtpy.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import napari.viewer


class CollapsibleSectionContainer(QWidget):
    """A collapsible section that can be oriented vertically or horizontally.

    Parameters
    ----------
    viewer : napari.viewer.Viewer
        The napari viewer instance.
    container_nake : str
        The name of the container.
    orientation : {'vertical', 'horizontal'}
        The orientation of the container. Vertical containers expand downward
        with horizontal scrolling. Horizontal containers expand rightward with
        vertical scrolling.
    """

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        container_name: str,
        parent: QWidget,
        orientation: Literal['vertical', 'horizontal'] = 'vertical',
        *,
        on_toggle: Callable[[bool], None] | None = None,
    ):
        super().__init__(parent=parent)
        self._viewer = viewer
        self._container_name = container_name
        self._on_toggle_callback = on_toggle
        self._orientation = orientation
        self._set_text = ' '

        # Create layout based on orientation
        layout_class = (
            QVBoxLayout if orientation == 'vertical' else QHBoxLayout
        )
        self._layout = layout_class(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(4)

        # Create button (rotated for horizontal orientation)
        button_class = (
            QPushButton if orientation == 'vertical' else RotatedButton
        )
        self._button = button_class(' ')
        font = self._button.font()
        font.setBold(True)
        self._button.setFont(font)
        self._button.setCheckable(True)
        self._button.toggled.connect(self._expanding_area_set_visible)
        self._layout.addWidget(self._button, 0)

        # Create expanding area
        self._expanding_area = QScrollArea(self)
        self._expanding_area.setWidgetResizable(True)

        if orientation == 'vertical':
            self._expanding_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self._expanding_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            # Disable wheel scrolling on horizontal scrollbar for vertical containers
            self.disable_horizontal_scrolling_wheel_filter = (
                DisableWheelScrollingFilter()
            )
            h_scrollbar = self._expanding_area.horizontalScrollBar()
            if h_scrollbar is not None:
                h_scrollbar.installEventFilter(
                    self.disable_horizontal_scrolling_wheel_filter
                )
            self._expanding_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        else:  # horizontal
            self._expanding_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._expanding_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self._expanding_area.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
            self._expanding_area.setFixedWidth(0)

        self._expanding_area.setVisible(False)
        self._layout.addWidget(
            self._expanding_area, 0 if orientation == 'vertical' else 1
        )

    def _expanding_area_set_visible(self, checked: bool) -> None:
        """Toggle the visibility of the expanding area."""
        self._expanding_area.setVisible(checked)
        self._sync_body_size()

        if self._on_toggle_callback is not None:
            self._on_toggle_callback(checked)

        # Update button text
        if not checked:
            self._button.setText('▶ ' + self._set_text)
        else:
            self._button.setText('▼ ' + self._set_text)

        self._expanding_area.updateGeometry()
        self.updateGeometry()

    def _sync_body_size(self) -> None:
        """Synchronize the expanding area size based on orientation."""
        current_widget = self._expanding_area.widget()

        if not self._expanding_area.isVisible() or current_widget is None:
            if self._orientation == 'vertical':
                self._expanding_area.setFixedHeight(0)
            else:
                self._expanding_area.setFixedWidth(0)
            return

        if self._orientation == 'vertical':
            widget_height = current_widget.sizeHint().height()
            h_scrollbar = self._expanding_area.horizontalScrollBar()
            scroll_bar_height = (
                h_scrollbar.sizeHint().height()
                if h_scrollbar is not None
                else 0
            )
            frame = 2 * self._expanding_area.frameWidth()
            self._expanding_area.setFixedHeight(
                widget_height + scroll_bar_height + frame
            )
        else:  # horizontal
            widget_width = current_widget.sizeHint().width()
            v_scrollbar = self._expanding_area.verticalScrollBar()
            scroll_bar_width = (
                v_scrollbar.sizeHint().width()
                if v_scrollbar is not None
                else 0
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

        if self._orientation == 'vertical':
            setting_widget.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
            )
            self._expanding_area.setWidget(setting_widget)
        else:  # horizontal
            # Horizontal containers need a wrapper with stretch
            wrapper = QWidget(self._expanding_area)
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(setting_widget)
            wrapper_layout.addStretch(1)
            self._expanding_area.setWidget(wrapper)

        self._sync_body_size()

    def _set_button_text(self, button_text: str) -> None:
        self._set_text = button_text
        self._expanding_area_set_visible(False)

    def expandedHeight(self) -> int:
        if self._orientation != 'vertical':
            return 0
        current_widget = self._expanding_area.widget()
        if not self.isExpanded() or current_widget is None:
            return 0
        return max(1, current_widget.sizeHint().height())

    def expandedWidth(self) -> int:
        if self._orientation != 'horizontal':
            return 0
        current_widget = self._expanding_area.widget()
        if not self.isExpanded() or current_widget is None:
            return 0
        return max(1, current_widget.sizeHint().width())


class RotatedButton(QPushButton):
    """A button that renders text rotated 90 degrees counterclockwise.

    Used for horizontal collapsible sections to save space.
    """

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

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
        return size.transposed()

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


class DisableWheelScrollingFilter(QObject):
    """Event filter to disable mouse wheel scrolling on scroll bars."""

    def eventFilter(self, a0, a1):
        return bool(a1 is not None and a1.type() == QEvent.Type.Wheel)
