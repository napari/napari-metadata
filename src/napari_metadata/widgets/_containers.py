"""Container widgets for napari-metadata.

``Orientation`` — type alias used by the collapsible section and the main widget.

``CollapsibleSectionContainer`` — a button-gated, scrollable content area
supporting both vertical and horizontal orientations.

``RotatedButton`` — a ``QPushButton`` that draws its label rotated 90°
counterclockwise, used as the header button for horizontal sections.

``HorizontalOnlyOuterScrollArea`` — an outer scroll area that constrains its
child to the viewport height and absorbs wheel events (so horizontal scrolling
is never triggered by the mouse wheel).

``DisableWheelScrollingFilter`` — an event filter that swallows wheel events
on a specific scrollbar, preventing accidental horizontal scroll inside a
vertical ``CollapsibleSectionContainer``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qtpy.QtCore import QEvent, QObject, QSize, Qt
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

#: Orientation of a ``CollapsibleSectionContainer`` (and the enclosing layout).
#: ``'vertical'`` sections expand downward; ``'horizontal'`` sections expand
#: rightward.  This alias is the single source of truth for both modules.
Orientation = Literal['vertical', 'horizontal']


class _ContentScrollArea(QScrollArea):
    """Scroll area whose size hint tracks its content widget.

    This lets the parent layout size the expanded section from the content's
    natural size without manually pinning fixed dimensions.
    """

    def __init__(
        self, orientation: Orientation, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._orientation = orientation

    def sizeHint(self) -> QSize:
        widget = self.widget()
        if widget is None:
            return super().sizeHint()

        hint = widget.sizeHint()
        frame = 2 * self.frameWidth()
        if self._orientation == 'vertical':
            # Minimum width (parent stretches horizontally) but preferred
            # height (avoid inner scrolling when possible).
            min_hint = widget.minimumSizeHint()
            return QSize(min_hint.width() + frame, hint.height() + frame)
        # Horizontal: preferred width; zero height (parent controls it).
        return QSize(hint.width() + frame, 0)

    def minimumSizeHint(self) -> QSize:
        widget = self.widget()
        if widget is None:
            return super().minimumSizeHint()

        hint = widget.minimumSizeHint()
        frame = 2 * self.frameWidth()
        if self._orientation == 'vertical':
            return QSize(0, hint.height() + frame)
        return QSize(0, 0)


class CollapsibleSectionContainer(QWidget):
    """A titled, collapsible section that can be oriented vertically or
    horizontally.

    Vertical sections expand *downward* (suitable for left/right dock areas).
    Horizontal sections expand *rightward* (suitable for top/bottom dock areas).

    Parameters
    ----------
    parent : QWidget
        Owning parent widget.
    title : str
        Text shown on the toggle button.
    orientation : {'vertical', 'horizontal'}
        Layout direction.  Defaults to ``'vertical'``.
    on_toggle : callable, optional
        Called with ``checked: bool`` whenever the section is expanded or
        collapsed.
    """

    def __init__(
        self,
        parent: QWidget,
        title: str,
        orientation: Orientation = 'vertical',
        *,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._on_toggle_callback = on_toggle
        self._orientation = orientation
        self._title = title
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum
            if orientation == 'vertical'
            else QSizePolicy.Policy.Expanding,
        )

        # Outer layout — vertical stacks button above content;
        # horizontal places button beside content.
        layout_class = (
            QVBoxLayout if orientation == 'vertical' else QHBoxLayout
        )
        self._layout = layout_class(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(4)

        # Toggle button — rotated for horizontal sections to save vertical space.
        button_class = (
            QPushButton if orientation == 'vertical' else RotatedButton
        )
        self._button: QPushButton = button_class('')
        if orientation == 'vertical':
            self._button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        font = self._button.font()
        font.setBold(True)
        self._button.setFont(font)
        self._button.setCheckable(True)
        self._button.toggled.connect(self._on_button_toggled)
        self._layout.addWidget(self._button, 0)

        # Expanding content area
        self._expanding_area = _ContentScrollArea(orientation, self)

        if orientation == 'vertical':
            self._expanding_area.setWidgetResizable(True)
            self._expanding_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._expanding_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            # Prevent the horizontal scrollbar from consuming mouse-wheel events
            # that should scroll the outer container.
            self._wheel_filter = DisableWheelScrollingFilter()
            h_scrollbar = self._expanding_area.horizontalScrollBar()
            if h_scrollbar is not None:
                h_scrollbar.installEventFilter(self._wheel_filter)
            self._expanding_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
            )
        else:  # horizontal
            self._expanding_area.setWidgetResizable(True)
            self._expanding_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._expanding_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._expanding_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

        self._expanding_area.setVisible(False)
        # Stretch factor 1 for horizontal so the content area fills available space
        self._layout.addWidget(
            self._expanding_area, 0 if orientation == 'vertical' else 1
        )

        # Initialise button text with the collapsed indicator.
        self._button.setText(f'\u25b6 {title}')

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_content_widget(self, widget: QWidget) -> None:
        """Set (or replace) the widget shown inside the collapsible area.

        The previous content widget, if any, is scheduled for deletion.
        For horizontal sections a wrapper with a vertical stretch is inserted
        automatically so the content stays top-aligned.
        """
        old = self._expanding_area.takeWidget()
        if old is not None:
            old.deleteLater()

        if self._orientation == 'vertical':
            widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self._expanding_area.setWidget(widget)
        else:  # horizontal — wrap to keep content top-aligned
            wrapper = QWidget(self._expanding_area)
            wrapper.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(widget)
            wrapper_layout.addStretch(1)
            self._expanding_area.setWidget(wrapper)

    def isExpanded(self) -> bool:
        """Return ``True`` if the section is currently expanded."""
        return self._button.isChecked()

    def setExpanded(self, checked: bool) -> None:
        """Expand or collapse the section programmatically.

        Equivalent to clicking the toggle button; the ``on_toggle`` callback
        and button-text update are performed automatically.
        """
        self._button.setChecked(checked)

    def sizeHint(self) -> QSize:
        return self._section_size_hint(minimum=False)

    def minimumSizeHint(self) -> QSize:
        return self._section_size_hint(minimum=True)

    def set_horizontal_section_width(self, width: int) -> None:
        """Apply a computed total width for horizontal layout.

        The width is dynamic and derived from the available viewport width,
        not a hardcoded constant.
        """
        if self._orientation != 'horizontal':
            return
        collapsed_width = self.collapsed_width_hint()
        self.setFixedWidth(max(collapsed_width, width))

    def set_vertical_section_height(self, height: int) -> None:
        """Apply a computed total height for vertical layout."""
        if self._orientation != 'vertical':
            return
        collapsed_height = self.collapsed_height_hint()
        self.setFixedHeight(max(collapsed_height, height))

    def collapsed_width_hint(self) -> int:
        margins = self._layout.contentsMargins()
        return (
            margins.left() + margins.right() + self._button.sizeHint().width()
        )

    def collapsed_height_hint(self) -> int:
        margins = self._layout.contentsMargins()
        return (
            margins.top() + margins.bottom() + self._button.sizeHint().height()
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _section_size_hint(self, *, minimum: bool) -> QSize:
        button_hint = (
            self._button.minimumSizeHint()
            if minimum
            else self._button.sizeHint()
        )
        if not self._button.isChecked():
            content_hint = QSize(0, 0)
        else:
            content_hint = (
                self._expanding_area.minimumSizeHint()
                if minimum
                else self._expanding_area.sizeHint()
            )

        margins = self._layout.contentsMargins()
        width = margins.left() + margins.right()
        height = margins.top() + margins.bottom()
        spacing = self._layout.spacing() if self._button.isChecked() else 0

        if self._orientation == 'vertical':
            width += max(button_hint.width(), content_hint.width())
            height += button_hint.height() + spacing + content_hint.height()
        else:
            width += button_hint.width() + spacing + content_hint.width()
            height += max(button_hint.height(), content_hint.height())

        return QSize(width, height)

    def _on_button_toggled(self, checked: bool) -> None:
        """Respond to the toggle button state change."""
        self._expanding_area.setVisible(checked)

        if self._on_toggle_callback is not None:
            self._on_toggle_callback(checked)

        indicator = '\u25bc' if checked else '\u25b6'
        self._button.setText(f'{indicator} {self._title}')
        self._expanding_area.updateGeometry()
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.updateGeometry()


class RotatedButton(QPushButton):
    """A ``QPushButton`` that renders its label rotated 90° counterclockwise.

    Used as the header button for horizontal ``CollapsibleSectionContainer``
    instances, keeping the button narrow while still readable.
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

    def paintEvent(self, a0) -> None:
        painter = QStylePainter(self)
        painter.rotate(-90)
        painter.translate(-self.height(), 0)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.rect = opt.rect.transposed()

        painter.drawControl(QStyle.ControlElement.CE_PushButton, opt)

    def sizeHint(self):
        return super().sizeHint().transposed()

    def minimumSizeHint(self):
        return self.sizeHint()


class HorizontalOnlyOuterScrollArea(QScrollArea):
    """A scroll area that constrains its child height and ignores wheel events.

    Used as the outermost scroll area in horizontal dock layouts.  The child is
    pinned to the viewport height (no vertical scroll) and wheel events are
    passed to the parent so the outer container can handle them.
    """

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        w = self.widget()
        if w is not None:
            w.setFixedHeight(self.viewport().height())

    def wheelEvent(self, a0: QWheelEvent | None) -> None:
        if a0 is not None:
            a0.ignore()


class DisableWheelScrollingFilter(QObject):
    """Event filter that swallows wheel events on a specific scrollbar.

    Install on a ``QScrollBar`` to prevent mouse-wheel events from
    accidentally scrolling that bar.
    """

    def eventFilter(self, a0, a1) -> bool:
        return bool(a1 is not None and a1.type() == QEvent.Type.Wheel)
