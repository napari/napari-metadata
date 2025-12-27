from collections.abc import Callable
from typing import Optional, Protocol

from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QDoubleValidator, QValidator
from qtpy.QtWidgets import QGridLayout, QLineEdit, QWidget


class CompactLineEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editingFinished.connect(self._moveCursorToStart)

    def _moveCursorToStart(self) -> None:
        self.setCursorPosition(0)

    def sizeHint(self) -> QSize:
        return self.minimumSizeHint()


class DoubleLineEdit(CompactLineEdit):
    valueChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setValidator(QDoubleValidator())
        self.editingFinished.connect(self.valueChanged)

    def minimumSizeHint(self) -> QSize:
        width_hint = self.fontMetrics().horizontalAdvance('1.234567')
        sizeHint = super().minimumSizeHint()
        return QSize(width_hint, sizeHint.height())

    def setText(self, text: str) -> None:
        self.setValue(float(text))

    def setValue(self, value: float) -> None:
        text = str(value)
        state, text, _ = self.validator().validate(text, 0)
        if state != QValidator.State.Acceptable:
            raise ValueError('Value is invalid.')
        if text != self.text():
            super().setText(text)
            self.editingFinished.emit()

    def value(self) -> float:
        return float(self.text())


class ReadOnlyLineEdit(CompactLineEdit):
    def __init__(self, *, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet('QLineEdit{background: transparent;}')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def setText(self, text: str) -> None:
        super().setText(text)
        self._moveCursorToStart()


def readonly_lineedit(text: Optional[str] = None) -> QLineEdit:
    widget = ReadOnlyLineEdit()
    if text is not None:
        widget.setText(text)
    return widget


class GridRow(Protocol):
    def widgets() -> tuple[QWidget, ...]: ...


def set_row_visible(row: GridRow, visible: bool) -> None:
    for w in row.widgets():
        w.setVisible(visible)


def update_num_rows(
    *,
    rows: list[GridRow],
    layout: QGridLayout,
    desired_num: int,
    row_factory: Callable[[], GridRow],
) -> None:
    current_num = len(rows)
    # Add any missing widgets.
    for _ in range(desired_num - current_num):
        row = row_factory()
        index = layout.count()
        for col, w in enumerate(row.widgets()):
            layout.addWidget(w, index, col)
        rows.append(row)
    # Remove any unneeded widgets.
    for _ in range(current_num - 1, desired_num - 1, -1):
        row = rows.pop()
        for w in row.widgets():
            layout.removeWidget(w)
