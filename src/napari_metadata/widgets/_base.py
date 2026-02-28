"""Base classes and data structures for axis metadata components.

``LayoutEntry`` replaces the deeply nested dict return type used by the
old ``get_entries_dict`` API.  ``AxisComponentBase`` provides the shared
lifecycle, layout, and inheritance logic that every per-axis component
needs — subclasses only override five template methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QLabel, QWidget

from napari_metadata.layer_utils import (
    get_axes_labels,
    get_layer_dimensions,
    resolve_layer,
)

if TYPE_CHECKING:
    from napari.layers import Layer
    from napari.viewer import ViewerModel


@dataclass
class LayoutEntry:
    """One cell (or stacked group of widgets) in the axis grid layout.

    Parameters
    ----------
    widgets : list[QWidget]
        Widgets occupying this cell.  Usually one, but ``AxisUnits`` stacks
        a ``QComboBox`` and a ``QLineEdit`` in the same cell.
    row_span : int
        Number of grid rows.
    col_span : int
        Number of grid columns.
    alignment : Qt.AlignmentFlag
        Hint for alignment inside the cell.
    """

    widgets: list[QWidget]
    row_span: int = 1
    col_span: int = 1
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter


class AxisComponentBase(ABC):
    """Abstract base for per-axis metadata editing components.

    Each concrete subclass manages one kind of per-axis data (labels,
    scales, translations, units).  The base class provides:

    * **Widget lifecycle** — ``load_entries`` drives ``_create_widgets``
      (new layer) or ``_refresh_values`` (same layer).
    * **Layout** — ``get_layout_entries`` returns a flat list of
      ``LayoutEntry`` per axis, consumable by ``_main.py``'s grid builder.
    * **Inheritance** — ``inherit_layer_properties`` merges current and
      template layer values based on per-axis checkbox states.
    * **Cross-component sync** — ``update_axis_name_labels`` refreshes
      the axis-name QLabels from the layer (``AxisLabels`` overrides
      this to no-op since it *is* the label editor).

    Subclasses must implement the five abstract template methods listed
    below.
    """

    #: Bold header text shown next to the component (e.g. ``"Scale:"``).
    #: Set as a class variable in each subclass.
    _label_text: str

    def __init__(
        self,
        viewer: ViewerModel,
        main_widget: QWidget,
    ) -> None:
        self._napari_viewer: ViewerModel = viewer
        self._main_widget = main_widget
        self._selected_layer: Layer | None = None

        self._component_qlabel = QLabel(self._label_text)
        self._component_qlabel.setStyleSheet('font-weight: bold')
        self._component_qlabel.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._axis_name_labels: list[QLabel] = []
        self._inherit_checkboxes: list[QCheckBox] = []

    # ------------------------------------------------------------------
    # Public API (consumed by _main.py / AxisMetadata coordinator)
    # ------------------------------------------------------------------

    @property
    def component_label(self) -> QLabel:
        """Bold header ``QLabel`` for this component (e.g. ``"Scale:"``)."""
        return self._component_qlabel

    @property
    def num_axes(self) -> int:
        """Number of per-axis widget rows currently alive (0 when empty)."""
        return len(self._axis_name_labels)

    def load_entries(self, layer: Layer | None = None) -> None:
        """Load or refresh widgets for *layer* (defaults to active layer).

        * Layer changed or ``None`` → destroy old widgets, create new ones.
        * Same layer → refresh existing widget values in place.
        """
        active_layer = resolve_layer(self._napari_viewer, layer)
        if active_layer != self._selected_layer or active_layer is None:
            self._clear_widgets()
            if active_layer is not None:
                self._create_widgets(active_layer)
            return
        self._refresh_values(active_layer)

    def get_layout_entries(self, axis_index: int) -> list[LayoutEntry]:
        """Return ``LayoutEntry`` items for one axis row.

        Default: ``[name_label, *value_entries, inherit_checkbox]``.
        """
        entries: list[LayoutEntry] = [
            LayoutEntry(widgets=[self._axis_name_labels[axis_index]]),
        ]
        entries.extend(self._get_value_entries(axis_index))
        entries.append(
            LayoutEntry(widgets=[self._inherit_checkboxes[axis_index]]),
        )
        return entries

    def update_axis_name_labels(self) -> None:
        """Refresh axis-name ``QLabel`` texts from the current layer.

        ``AxisLabels`` overrides this to no-op because it shows axis
        *indices*, not axis *names*.
        """
        labels = get_axes_labels(self._napari_viewer)
        for i, label in enumerate(labels):
            if i >= len(self._axis_name_labels):
                break
            self._axis_name_labels[i].setText(label if label else str(i))

    def set_checkboxes_visible(self, visible: bool) -> None:
        """Show or hide the per-axis inheritance checkboxes."""
        for cb in self._inherit_checkboxes:
            cb.setVisible(visible)

    def inherit_layer_properties(self, template_layer: Layer) -> None:
        """Merge current and template values based on checkbox states.

        Checked axes receive the template value; unchecked keep current.
        Resets ``_selected_layer`` so the next ``load_entries`` call fully
        rebuilds widgets with the merged values.
        """
        current_layer = resolve_layer(self._napari_viewer)
        if current_layer is None:
            return
        current_values = self._get_layer_values(current_layer)
        template_values = self._get_layer_values(template_layer)
        merged: list[Any] = [
            tv if self._inherit_checkboxes[i].isChecked() else cv
            for i, (cv, tv) in enumerate(
                zip(current_values, template_values, strict=False)
            )
        ]
        self._apply_values(merged)
        # Force full rebuild on next load_entries.
        self._selected_layer = None

    # ------------------------------------------------------------------
    # Template methods — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def _create_widgets(self, layer: Layer) -> None:
        """Create all per-axis widgets for *layer*.

        Must populate ``_axis_name_labels``, ``_inherit_checkboxes``,
        and any component-specific widget lists.  Must set
        ``self._selected_layer = layer`` at the end.
        """

    @abstractmethod
    def _refresh_values(self, layer: Layer) -> None:
        """Update existing widget values from *layer* without recreating."""

    @abstractmethod
    def _get_value_entries(self, axis_index: int) -> list[LayoutEntry]:
        """Return ``LayoutEntry`` items for the editable widget(s) at *axis_index*."""

    @abstractmethod
    def _get_layer_values(self, layer: Layer) -> tuple:
        """Read the axis property tuple from *layer* (used by inheritance)."""

    @abstractmethod
    def _apply_values(self, values: list) -> None:
        """Write merged axis property values to the active layer."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_widget_lists(self) -> list[list[QWidget]]:
        """Return all per-axis widget lists for cleanup.

        Subclasses override to include their own lists (spinboxes, etc.)
        and must call ``super()._all_widget_lists()`` to include the
        base lists.
        """
        return [self._axis_name_labels, self._inherit_checkboxes]

    def _clear_widgets(self) -> None:
        """Destroy all per-axis widgets and reset ``_selected_layer``."""
        for widget_list in self._all_widget_lists():
            for w in widget_list:
                w.setParent(None)
                w.deleteLater()
            widget_list.clear()
        self._selected_layer = None

    def _create_axis_name_labels(self, layer: Layer) -> None:
        """Create per-axis name QLabels from the layer's axis labels.

        Shows the axis label text, falling back to the axis index when
        the label is empty.
        """
        labels = get_axes_labels(self._napari_viewer, layer)
        for i, label in enumerate(labels):
            qlabel = QLabel(label if label else str(i))
            qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._axis_name_labels.append(qlabel)

    def _create_inherit_checkboxes(self, layer: Layer) -> None:
        """Create one inherit ``QCheckBox`` per axis (all checked)."""
        for _ in range(get_layer_dimensions(layer)):
            cb = QCheckBox('')
            cb.setChecked(True)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._inherit_checkboxes.append(cb)
