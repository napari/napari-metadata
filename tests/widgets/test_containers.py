"""Tests for napari_metadata.widgets._containers."""

from __future__ import annotations

import pytest

from napari_metadata.widgets._containers import (
    CollapsibleSectionContainer,
    DisableWheelScrollingFilter,
    HorizontalOnlyOuterScrollArea,
    Orientation,
    RotatedButton,
)

ORIENTATIONS: list[Orientation] = ['vertical', 'horizontal']


class TestCollapsibleSectionContainerInit:
    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_starts_collapsed(self, qtbot, orientation):
        w = CollapsibleSectionContainer(None, 'My Section', orientation)
        qtbot.addWidget(w)
        assert not w.isExpanded()

    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_initial_button_text_has_right_arrow(self, qtbot, orientation):
        w = CollapsibleSectionContainer(None, 'My Section', orientation)
        qtbot.addWidget(w)
        assert '\u25b6' in w._button.text()
        assert 'My Section' in w._button.text()

    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_expanding_area_hidden_initially(self, qtbot, orientation):
        w = CollapsibleSectionContainer(None, 'My Section', orientation)
        qtbot.addWidget(w)
        assert w._expanding_area.isHidden()

    def test_default_orientation_is_vertical(self, qtbot):
        w = CollapsibleSectionContainer(None, 'Default')
        qtbot.addWidget(w)
        assert w._orientation == 'vertical'

    def test_explicit_horizontal_orientation(self, qtbot):
        w = CollapsibleSectionContainer(None, 'H', 'horizontal')
        qtbot.addWidget(w)
        assert w._orientation == 'horizontal'

    def test_button_is_checkable(self, qtbot):
        w = CollapsibleSectionContainer(None, 'T')
        qtbot.addWidget(w)
        assert w._button.isCheckable()

    def test_no_callback_by_default(self, qtbot):
        # Toggling without a callback must not raise.
        w = CollapsibleSectionContainer(None, 'T')
        qtbot.addWidget(w)
        w._button.setChecked(True)  # should not raise


class TestCollapsibleSectionContainerToggle:
    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_toggle_expands(self, qtbot, orientation):
        w = CollapsibleSectionContainer(None, 'T', orientation)
        qtbot.addWidget(w)
        w._button.setChecked(True)
        assert w.isExpanded()
        # isHidden() is False once setVisible(True) is called, even without
        # a top-level window being shown.
        assert not w._expanding_area.isHidden()

    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_toggle_collapses_again(self, qtbot, orientation):
        w = CollapsibleSectionContainer(None, 'T', orientation)
        qtbot.addWidget(w)
        w._button.setChecked(True)
        w._button.setChecked(False)
        assert not w.isExpanded()
        assert w._expanding_area.isHidden()

    def test_expanded_button_text_has_down_arrow(self, qtbot):
        w = CollapsibleSectionContainer(None, 'Sec')
        qtbot.addWidget(w)
        w._button.setChecked(True)
        assert '\u25bc' in w._button.text()
        assert 'Sec' in w._button.text()

    def test_collapsed_button_text_returns_to_right_arrow(self, qtbot):
        w = CollapsibleSectionContainer(None, 'Sec')
        qtbot.addWidget(w)
        w._button.setChecked(True)
        w._button.setChecked(False)
        assert '\u25b6' in w._button.text()

    def test_on_toggle_callback_called_on_expand(self, qtbot):
        calls: list[bool] = []
        w = CollapsibleSectionContainer(None, 'T', on_toggle=calls.append)
        qtbot.addWidget(w)
        w._button.setChecked(True)
        assert calls == [True]

    def test_on_toggle_callback_called_on_collapse(self, qtbot):
        calls: list[bool] = []
        w = CollapsibleSectionContainer(None, 'T', on_toggle=calls.append)
        qtbot.addWidget(w)
        w._button.setChecked(True)
        w._button.setChecked(False)
        assert calls == [True, False]


class TestSetContentWidget:
    from qtpy.QtWidgets import QLabel

    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_set_content_widget_attaches_widget(self, qtbot, orientation):
        from qtpy.QtWidgets import QLabel

        w = CollapsibleSectionContainer(None, 'T', orientation)
        qtbot.addWidget(w)
        label = QLabel('hello')
        w.set_content_widget(label)
        # After setting, the expanding area has a widget.
        assert w._expanding_area.widget() is not None

    def test_replace_content_widget(self, qtbot):
        from qtpy.QtWidgets import QLabel

        w = CollapsibleSectionContainer(None, 'T')
        qtbot.addWidget(w)
        first = QLabel('first')
        w.set_content_widget(first)
        second = QLabel('second')
        w.set_content_widget(second)
        # The new widget is installed; old one is gone.
        current = w._expanding_area.widget()
        assert current is not None


class TestRotatedButton:
    def test_size_hint_is_transposed(self, qtbot):
        btn = RotatedButton('Hello')
        qtbot.addWidget(btn)
        normal = btn.__class__.__bases__[0].sizeHint(
            btn
        )  # QPushButton.sizeHint
        rotated = btn.sizeHint()
        assert rotated.width() == normal.height()
        assert rotated.height() == normal.width()

    def test_minimum_size_hint_equals_size_hint(self, qtbot):
        btn = RotatedButton('Hello')
        qtbot.addWidget(btn)
        assert btn.minimumSizeHint() == btn.sizeHint()


class TestHorizontalOnlyOuterScrollArea:
    def test_wheel_event_is_ignored(self, qtbot):
        """Wheel event must be flagged as ignored (propagated to parent)."""
        from qtpy.QtCore import QPoint, QPointF, Qt
        from qtpy.QtGui import QWheelEvent

        area = HorizontalOnlyOuterScrollArea()
        qtbot.addWidget(area)

        event = QWheelEvent(
            QPointF(0, 0),
            QPointF(0, 0),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        area.wheelEvent(event)
        assert not event.isAccepted()

    def test_wheel_event_none_does_not_raise(self, qtbot):
        area = HorizontalOnlyOuterScrollArea()
        qtbot.addWidget(area)
        area.wheelEvent(None)  # must not raise


class TestDisableWheelScrollingFilter:
    def test_blocks_wheel_events(self, qtbot):
        from qtpy.QtCore import QEvent, QObject

        f = DisableWheelScrollingFilter()
        target = QObject()

        class _FakeEvent:
            def type(self):
                return QEvent.Type.Wheel

        assert f.eventFilter(target, _FakeEvent()) is True

    def test_passes_non_wheel_events(self, qtbot):
        from qtpy.QtCore import QEvent, QObject

        f = DisableWheelScrollingFilter()
        target = QObject()

        class _FakeEvent:
            def type(self):
                return QEvent.Type.MouseButtonPress

        assert f.eventFilter(target, _FakeEvent()) is False

    def test_none_event_does_not_raise(self, qtbot):
        from qtpy.QtCore import QObject

        f = DisableWheelScrollingFilter()
        target = QObject()
        result = f.eventFilter(target, None)
        assert result is False


def test_orientation_literal_values():
    """Orientation is a public name that external code can import."""
    from typing import get_args

    args = get_args(Orientation)
    assert set(args) == {'vertical', 'horizontal'}
