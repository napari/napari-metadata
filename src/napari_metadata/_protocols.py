from typing import Protocol, TYPE_CHECKING

from qtpy.QtWidgets import (
    QWidget,
    QCheckBox,
)

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


""" This protocol is used to define the structure of the AxisComponent class.
NOTE: Again, it is possible to integrate the metadata into a single type of component by passing lists instead of single values in the get_entries_dict,
but it might complicate even more the already complicated extension patterns."""


class AxisComponent(Protocol):
    _axis_component_name: str
    _entries_dict: dict[int, dict[str, tuple[int, int, QWidget, str | None]]]
    _napari_viewer: 'ViewerModel'

    def __init__(self, napari_viewer: 'ViewerModel') -> None: ...
    def load_entries(
        self,
    ) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]] | None: ...
    def get_entries_dict(
        self,
    ) -> dict[int, dict[str, tuple[int, int, QWidget, str | None]]]: ...
    def get_rows_and_column_spans(self) -> dict[str, int] | None: ...
    def get_checkboxes_list(self) -> list[QCheckBox]: ...
    def inherit_layer_properties(self, template_layer: 'Layer') -> None: ...


class MetadataWidgetAPI(Protocol):
    def apply_inheritance_to_current_layer(
        self, template_layer: 'Layer'
    ) -> None: ...
