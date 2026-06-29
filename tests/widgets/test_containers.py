"""Tests for napari_metadata.widgets._containers."""

from __future__ import annotations

import pytest
from qtpy.QtCore import Qt

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

    def test_vertical_content_area_uses_content_size_hint(self, qtbot):
        from qtpy.QtCore import QSize
        from qtpy.QtWidgets import QWidget

        class _HintWidget(QWidget):
            def sizeHint(self):
                return QSize(120, 80)

        w = CollapsibleSectionContainer(None, 'T', 'vertical')
        qtbot.addWidget(w)
        content = _HintWidget()
        w.set_content_widget(content)

        expected = (
            content.sizeHint().height() + 2 * w._expanding_area.frameWidth()
        )
        assert w._expanding_area.sizeHint().height() == expected
        assert w._expanding_area.sizeHint().width() > 0

    def test_horizontal_content_area_uses_wrapper_size_hint(self, qtbot):
        from qtpy.QtWidgets import QLabel

        w = CollapsibleSectionContainer(None, 'T', 'horizontal')
        qtbot.addWidget(w)
        content = QLabel('hello')
        w.set_content_widget(content)

        wrapper = w._expanding_area.widget()
        assert wrapper is not None
        expected = (
            wrapper.sizeHint().width() + 2 * w._expanding_area.frameWidth()
        )
        assert w._expanding_area.sizeHint().width() == expected
        assert w._expanding_area.sizeHint().height() == 0

    @pytest.mark.parametrize('orientation', ORIENTATIONS)
    def test_content_area_falls_back_to_base_hints_without_widget(
        self, qtbot, orientation
    ):
        w = CollapsibleSectionContainer(None, 'T', orientation)
        qtbot.addWidget(w)

        assert w._expanding_area.widget() is None
        assert w._expanding_area.sizeHint().isValid()
        assert w._expanding_area.minimumSizeHint().isValid()


class TestScrollPolicies:
    def test_vertical_sections_allow_visible_vertical_scrolling(self, qtbot):
        w = CollapsibleSectionContainer(None, 'T', 'vertical')
        qtbot.addWidget(w)
        assert (
            w._expanding_area.verticalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

    def test_horizontal_sections_allow_inner_horizontal_scrolling(self, qtbot):
        w = CollapsibleSectionContainer(None, 'T', 'horizontal')
        qtbot.addWidget(w)
        assert (
            w._expanding_area.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        assert w._expanding_area.widgetResizable()

    def test_vertical_section_button_expands_with_parent_width(self, qtbot):
        from qtpy.QtWidgets import QVBoxLayout, QWidget

        parent = QWidget()
        parent.resize(320, 200)
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        w = CollapsibleSectionContainer(parent, 'T', 'vertical')
        layout.addWidget(w)
        qtbot.addWidget(parent)
        parent.show()
        qtbot.waitExposed(parent)

        assert w._button.width() >= parent.width() - 20

    def test_horizontal_width_setter_is_ignored_for_vertical_sections(
        self, qtbot
    ):
        w = CollapsibleSectionContainer(None, 'T', 'vertical')
        qtbot.addWidget(w)

        before = w.maximumWidth()
        w.set_horizontal_section_width(200)

        assert w.maximumWidth() == before

    def test_vertical_height_setter_is_ignored_for_horizontal_sections(
        self, qtbot
    ):
        w = CollapsibleSectionContainer(None, 'T', 'horizontal')
        qtbot.addWidget(w)

        before = w.maximumHeight()
        w.set_vertical_section_height(200)

        assert w.maximumHeight() == before


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
    def test_resize_event_pins_child_height_to_viewport(self, qtbot):
        from qtpy.QtWidgets import QWidget

        area = HorizontalOnlyOuterScrollArea()
        content = QWidget()
        area.setWidget(content)
        area.resize(240, 160)
        qtbot.addWidget(area)

        area.show()
        qtbot.waitExposed(area)

        assert content.height() == area.viewport().height()

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
