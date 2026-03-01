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

#: Orientation of a ``CollapsibleSectionContainer`` (and the enclosing layout).
#: ``'vertical'`` sections expand downward; ``'horizontal'`` sections expand
#: rightward.  This alias is the single source of truth for both modules.
Orientation = Literal['vertical', 'horizontal']


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
        font = self._button.font()
        font.setBold(True)
        self._button.setFont(font)
        self._button.setCheckable(True)
        self._button.toggled.connect(self._on_button_toggled)
        self._layout.addWidget(self._button, 0)

        # Expanding content area
        self._expanding_area = QScrollArea(self)
        self._expanding_area.setWidgetResizable(True)

        if orientation == 'vertical':
            self._expanding_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
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
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
            )
            self._expanding_area.setWidget(widget)
        else:  # horizontal — wrap to keep content top-aligned
            wrapper = QWidget(self._expanding_area)
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(widget)
            wrapper_layout.addStretch(1)
            self._expanding_area.setWidget(wrapper)

        self._sync_size()

    def isExpanded(self) -> bool:
        """Return ``True`` if the section is currently expanded."""
        return self._button.isChecked()

    def setExpanded(self, checked: bool) -> None:
        """Expand or collapse the section programmatically.

        Equivalent to clicking the toggle button; the ``on_toggle`` callback
        and button-text update are performed automatically.
        """
        self._button.setChecked(checked)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_button_toggled(self, checked: bool) -> None:
        """Respond to the toggle button state change."""
        self._expanding_area.setVisible(checked)
        self._sync_size()

        if self._on_toggle_callback is not None:
            self._on_toggle_callback(checked)

        indicator = '\u25bc' if checked else '\u25b6'
        self._button.setText(f'{indicator} {self._title}')

        self._expanding_area.updateGeometry()
        self.updateGeometry()

    def _sync_size(self) -> None:
        """Fix the expanding area's size to match its content hint."""
        current_widget = self._expanding_area.widget()

        # Use the button's checked state as the authoritative "is expanded"
        # guard.  isVisible() would return False whenever an ancestor widget
        # is hidden (e.g. during programmatic rebuild before the dock is
        # shown), causing the size to be wrongly zeroed out.
        if not self._button.isChecked() or current_widget is None:
            if self._orientation == 'vertical':
                self._expanding_area.setFixedHeight(0)
            else:
                self._expanding_area.setFixedWidth(0)
            return

        if self._orientation == 'vertical':
            h_scrollbar = self._expanding_area.horizontalScrollBar()
            scrollbar_h = (
                h_scrollbar.sizeHint().height()
                if h_scrollbar is not None
                else 0
            )
            frame = 2 * self._expanding_area.frameWidth()
            # Activate the layout before reading sizeHint so the value is valid
            # even when the widget hasn't had a paint pass yet (e.g. during a
            # programmatic expand called from _do_rebuild_content).
            layout = current_widget.layout()
            if layout is not None:
                layout.activate()
            self._expanding_area.setFixedHeight(
                current_widget.sizeHint().height() + scrollbar_h + frame
            )
        else:  # horizontal
            v_scrollbar = self._expanding_area.verticalScrollBar()
            scrollbar_w = (
                v_scrollbar.sizeHint().width()
                if v_scrollbar is not None
                else 0
            )
            frame = 2 * self._expanding_area.frameWidth()
            layout = current_widget.layout()
            if layout is not None:
                layout.activate()
            self._expanding_area.setFixedWidth(
                current_widget.sizeHint().width() + scrollbar_w + frame
            )

        current_widget.updateGeometry()
        self._expanding_area.updateGeometry()
        self.updateGeometry()


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
