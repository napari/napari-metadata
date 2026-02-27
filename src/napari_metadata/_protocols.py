from typing import TYPE_CHECKING, Protocol

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QLabel, QWidget

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer


""" This protocol is used to define the structure of the AxisComponent class.
NOTE: Again, it is possible to integrate the metadata into a single type of component by passing lists instead of single values in the get_entries_dict,
but it might complicate even more the already complicated extension patterns."""


class AxisComponent(Protocol):
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _main_widget: QWidget
    _component_qlabel: QLabel

    _selected_layer: 'Layer | None'
    _axis_name_labels_tuple: tuple[QLabel, ...]
    _inherit_checkbox_tuple: tuple[QCheckBox, ...]

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None: ...
    def load_entries(self, layer: 'Layer | None' = None) -> None: ...
    def get_entries_dict(
        self,
    ) -> dict[
        int,
        dict[
            str, tuple[list[QWidget], int, int, str, Qt.AlignmentFlag | None]
        ],
    ]: ...
    def _reset_tuples(self) -> None: ...
    def _set_axis_name_labels(self) -> None: ...
    def _set_checkboxes_visibility(self, visible: bool) -> None: ...


"""This protocol is made to store the general metadata components that are not the axis components. They differn from the axis components
because they only get one widget per entry and I didn't wanto to complicate (complicate more) the extension patterns so it'll have to stay like this.
It might be best if the plugin won't allow the user to modify any of these except for the layer name.
NOTE: It is 100% possible to integrate them into a single type of component by passing lists instead of single values in the get_entries_dict but It might get too complex to extend?"""


class MetadataComponent(Protocol):
    _component_name: str
    _napari_viewer: 'ViewerModel'
    _component_qlabel: QLabel

    """All general metadata components should pass the napari viewer and the main widget (This is the MetaDataWidget that isn't declared until later... SOMEBODY
    SHOULD MAKE A PROTOCOL FOR THIS....). This is to make sure that the components can call methods from the MetaDataWidget in case they need to interact between components."""

    def __init__(
        self, napari_viewer: 'ViewerModel', main_widget: QWidget
    ) -> None: ...

    """I am suggesting the load_entries method to update/load anything that the component needs to display the information."""

    def load_entries(self, layer: 'Layer | None' = None) -> None: ...

    """ This method returns the dictionary that will be used to populate the general metadata QGridLayout.
    It requires you to input the type of layout, either horizontal or vertical, with vertical set to default.
    It should return a dictionary with the name of the entries as keys (They'll be set in bold capital letters) and a tuple with the corresponding
    QWidget, the row span, the column span, the calling method as a string or none if there's no method """

    def get_entries_dict(
        self, layout_mode: str
    ) -> (
        dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]]
        | dict[
            int,
            dict[str, tuple[QWidget, int, int, str, Qt.AlignmentFlag | None]],
        ]
    ): ...

    """ This method returns a boolean that will determine if the entry is to the left or below the name of the entry. """

    def get_under_label(self, layout_mode: str) -> bool: ...


class AxesMetadataComponentsInstanceAPI(Protocol):
    def _update_axes_labels(self) -> None: ...


class MetadataWidgetAPI(Protocol):
    def apply_inheritance_to_current_layer(
        self, template_layer: 'Layer'
    ) -> None: ...
    def load_axes_widgets(self) -> None: ...
    def get_axes_metadata_instance(
        self,
    ) -> AxesMetadataComponentsInstanceAPI: ...
