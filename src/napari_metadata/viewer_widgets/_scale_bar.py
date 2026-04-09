from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from qtpy.QtWidgets import QVBoxLayout, QWidget

from napari_metadata.viewer_widgets._base import ViewerComponentBase

if TYPE_CHECKING:
    from napari.components import ViewerModel


class ScaleBarMetadata:
    """Coordinator that owns the scale bar viewer components."""

    def __init__(
        self,
        napari_viewer: ViewerModel,
        parent_widget: QWidget,
        components: Sequence[ViewerComponentBase] | None = None,
    ) -> None:
        self._napari_viewer = napari_viewer
        self._parent_widget = parent_widget
        self._components = list(components) if components is not None else []

    @property
    def components(self) -> list[ViewerComponentBase]:
        """All scale bar components in display order."""
        return list(self._components)

    def refresh(self) -> None:
        """Refresh all managed components from the current viewer."""
        for component in self._components:
            component.load_entries(self._napari_viewer)


class ScaleBarWidget(QWidget):
    """Scale bar section of the viewer metadata widget."""

    def __init__(
        self,
        napari_viewer: ViewerModel,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self._napari_viewer = napari_viewer
        self._metadata = ScaleBarMetadata(napari_viewer, self)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.addStretch()
