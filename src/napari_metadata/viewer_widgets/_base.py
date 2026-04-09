"""Base classes for viewer metadata components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel


class ViewerComponentBase(ABC):
    """Abstract base for simple viewer metadata display components."""

    _label_text: str
    _tooltip_text: str = ''

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
    ) -> None:
        super().__init__()
        self._napari_viewer = napari_viewer
        self._parent_widget = parent_widget
        self._component_qlabel = QLabel(self._label_text, parent=parent_widget)
        self._component_qlabel.setStyleSheet('font-weight: bold')
        self._component_qlabel.setToolTip(self._tooltip_text)
        self._display_label = QLabel('', parent=parent_widget)
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

    @property
    def component_label(self) -> QLabel:
        """Bold header ``QLabel`` for this component."""
        return self._component_qlabel

    @property
    def value_widgets(self) -> list[QWidget]:
        """Widgets displayed to the right of the bold label."""
        return [self._display_label]

    def load_entries(self, viewer: ViewerModel | None = None) -> None:
        """Refresh the display from the current viewer state."""
        if viewer is not None:
            self._napari_viewer = viewer
        for widget in self.value_widgets:
            widget.setToolTip(self._tooltip_text)
        self._update_display()

    def clear(self) -> None:
        """Reset the display to an empty state."""
        self._display_label.setText('')

    def set_visible(self, visible: bool) -> None:
        """Show or hide both the header label and value widgets."""
        self.component_label.setVisible(visible)
        for widget in self.value_widgets:
            widget.setVisible(visible)

    def _update_display(self) -> None:
        """Update the default display widget from the bound viewer."""
        self._display_label.setText(self._get_display_text())

    @abstractmethod
    def _get_display_text(self) -> str:
        """Return the display string for the bound viewer."""
