"""Base classes and data structures for metadata components.

``ComponentBase`` is the root of the component hierarchy, providing
parent widget and bold header label shared by all components.

``AxisComponentBase`` adds per-axis widget lifecycle, layout, and
inheritance logic for editable axis components.

``FileComponentBase`` adds simple layer-display lifecycle for
read-only file metadata components.

``LayoutEntry`` replaces the deeply nested dict return type used by the
old ``get_entries_dict`` API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QLabel, QWidget

if TYPE_CHECKING:
    from napari.layers import Layer


class _WidgetCollection(Protocol):
    """Minimal widget collection interface needed for cleanup."""

    def __iter__(self) -> Iterator[QWidget]: ...

    def clear(self) -> None: ...


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


class ComponentBase(ABC):
    """Root abstract base for all metadata components.

    Provides:

    * Parent-widget reference
    * Bold header ``QLabel`` initialized from the ``_label_text``
      class variable
    * ``component_label`` property
    * ``load_entries`` lifecycle hook (abstract)
    """

    #: Bold header text shown next to the component (e.g. ``"Scale:"``).
    #: Set as a class variable in each subclass.
    _label_text: str

    #: Tooltip shown on the header label and value widget(s).
    #: Set as a class variable in each subclass; defaults to no tooltip.
    _tooltip_text: str = ''

    def __init__(
        self,
        parent_widget: QWidget,
    ) -> None:
        super().__init__()
        self._parent_widget = parent_widget

        self._component_qlabel = QLabel(self._label_text, parent=parent_widget)
        self._component_qlabel.setStyleSheet('font-weight: bold')
        self._component_qlabel.setToolTip(self._tooltip_text)

    @property
    def component_label(self) -> QLabel:
        """Bold header ``QLabel`` for this component (e.g. ``"Scale:"``)."""
        return self._component_qlabel

    @abstractmethod
    def load_entries(self, layer: Layer) -> None:
        """Load or refresh widget state for *layer*."""


class BoundLayerOwner:
    """Shared bound-layer state and validation helpers."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_layer: Layer | None = None

    def _bind_layer_reference(self, layer: Layer) -> None:
        self._selected_layer = layer

    def _unbind_layer_reference(self) -> None:
        self._selected_layer = None

    def _require_selected_layer(self) -> Layer:
        layer = self._selected_layer
        if layer is None:
            raise RuntimeError(
                f'{type(self).__name__} is not bound to a layer.'
            )
        return layer


class BoundLayerCoordinator(BoundLayerOwner, ABC):
    """Template lifecycle for coordinators that bind child components."""

    @property
    @abstractmethod
    def components(self) -> Sequence[Any]:
        """All bound child components managed by this coordinator."""

    def bind_layer(self, layer: Layer) -> None:
        """Bind the coordinator and all children to *layer*."""
        if layer is self._selected_layer:
            return
        if self._selected_layer is not None:
            self.unbind_layer()
        self._bind_layer_reference(layer)
        for component in self.components:
            component.bind_layer(layer)
        self._connect_bound_layer_events(layer)

    def unbind_layer(self) -> None:
        """Unbind the coordinator and all children from the current layer."""
        layer = self._selected_layer
        if layer is not None:
            self._disconnect_bound_layer_events(layer)
        self._unbind_layer_reference()
        for component in self.components:
            component.unbind_layer()

    @abstractmethod
    def _connect_bound_layer_events(self, layer: Layer) -> None:
        """Connect model events for the bound *layer*."""

    @abstractmethod
    def _disconnect_bound_layer_events(self, layer: Layer) -> None:
        """Disconnect model events for the previously bound *layer*."""


class AxisComponentBase(BoundLayerOwner, ComponentBase):
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
      the axis-name QLabels (or line edits for ``AxisLabels``) from the
      current layer when axis labels change.

    Subclasses must implement the five abstract template methods listed
    below.
    """

    def __init__(
        self,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(parent_widget)
        self._axis_name_labels: list[QLabel] = []
        self._inherit_checkboxes: list[QCheckBox] = []

    # ------------------------------------------------------------------
    # Public API (consumed by _main.py / AxisMetadata coordinator)
    # ------------------------------------------------------------------

    @property
    def num_axes(self) -> int:
        """Number of per-axis widget rows currently alive (0 when empty)."""
        return len(self._axis_name_labels)

    def load_entries(self, layer: Layer) -> None:
        """Refresh widgets for *layer*, binding first when needed."""
        if layer is not self._selected_layer:
            self.bind_layer(layer)
            return
        self._refresh_values(layer)

    def bind_layer(self, layer: Layer) -> None:
        """Bind this component to *layer* and create widgets if needed."""
        if layer is self._selected_layer and self.num_axes > 0:
            return
        self._clear_widgets()
        self._bind_layer_reference(layer)
        self._create_widgets(layer)

    def unbind_layer(self) -> None:
        """Clear widgets and remove any bound layer reference."""
        self._clear_widgets()
        self._unbind_layer_reference()

    def clear(self) -> None:
        """Destroy all per-axis widgets (used when no layer is active)."""
        self.unbind_layer()

    def get_layout_entries(self, axis_index: int) -> list[LayoutEntry]:
        """Return ``LayoutEntry`` items for one axis row.

        Default: ``[name_label, *value_entries, inherit_checkbox]``.
        """
        entries: list[LayoutEntry] = [
            LayoutEntry(widgets=[self._axis_name_labels[axis_index]]),
        ]
        value_entries = self._get_value_entries(axis_index)
        for entry in value_entries:
            for widget in entry.widgets:
                widget.setToolTip(self._tooltip_text)
        entries.extend(value_entries)
        entries.append(
            LayoutEntry(widgets=[self._inherit_checkboxes[axis_index]]),
        )
        return entries

    def update_axis_name_labels(self, layer: Layer) -> None:
        """Refresh axis-name ``QLabel`` texts from *layer*.

        ``AxisLabels`` overrides this to refresh its line edits instead.
        """
        labels = layer.axis_labels
        for i, label in enumerate(labels):
            if i >= len(self._axis_name_labels):
                break
            self._axis_name_labels[i].setText(label if label else str(i))

    def set_checkboxes_visible(self, visible: bool) -> None:
        """Show or hide the per-axis inheritance checkboxes."""
        for cb in self._inherit_checkboxes:
            cb.setVisible(visible)

    def inherit_layer_properties(
        self, template_layer: Layer, current_layer: Layer
    ) -> None:
        """Merge current and template values based on checkbox states.

        Checked axes receive the template value; unchecked keep current.
        The caller (``MetadataWidget.apply_inheritance_to_current_layer``)
        is responsible for triggering a page rebuild after all components
        have been updated.
        """
        current_values = self._get_layer_values(current_layer)
        template_values = self._get_layer_values(template_layer)
        merged: list[Any] = [
            tv if self._inherit_checkboxes[i].isChecked() else cv
            for i, (cv, tv) in enumerate(
                zip(current_values, template_values, strict=True)
            )
        ]
        self._apply_values(current_layer, merged)

    # ------------------------------------------------------------------
    # Template methods — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def _create_widgets(self, layer: Layer) -> None:
        """Create all per-axis widgets for *layer*.

        Must populate ``_axis_name_labels``, ``_inherit_checkboxes``,
        and any component-specific widget lists.
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
    def _apply_values(self, layer: Layer, values: list) -> None:
        """Write merged axis property values to *layer*."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_widget_lists(self) -> list[_WidgetCollection]:
        """Return all per-axis widget lists for cleanup.

        Subclasses override to include their own lists (spinboxes, etc.)
        and must call ``super()._all_widget_lists()`` to include the
        base lists.
        """
        return [self._axis_name_labels, self._inherit_checkboxes]

    def _clear_widgets(self) -> None:
        """Block signals and destroy all per-axis widgets.

        Signals are blocked before ``setParent(None)`` to prevent Qt
        focus-loss events (e.g. ``editingFinished``) from reaching
        handlers while widgets are being torn down.
        """
        for widget_list in self._all_widget_lists():
            for w in widget_list:
                w.blockSignals(True)
                w.setParent(None)
                w.deleteLater()
            widget_list.clear()

    def _create_axis_name_labels(self, layer: Layer) -> None:
        """Create per-axis name QLabels from the layer's axis labels.

        Shows the axis label text, falling back to the axis index when
        the label is empty.
        """
        labels = layer.axis_labels
        for i, label in enumerate(labels):
            qlabel = QLabel(
                label if label else str(i),
                parent=self._parent_widget,
            )
            qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._axis_name_labels.append(qlabel)

    def _create_inherit_checkboxes(self, layer: Layer) -> None:
        """Create one inherit ``QCheckBox`` per axis (all checked)."""
        for _ in range(layer.ndim):
            cb = QCheckBox('', parent=self._parent_widget)
            cb.setChecked(True)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._inherit_checkboxes.append(cb)


class FileComponentBase(ComponentBase):
    """Abstract base for file/layer metadata display components.

    Each concrete subclass presents one piece of layer information
    (name, shape, dtype, size, path).  The base class provides:

    * **Display lifecycle** — ``load_entries`` calls ``_update_display``.
    * **Default QLabel display** — simple read-only subclasses only need
      to implement ``_get_display_text``; the base handles the
      ``QLabel`` creation and update logic.
    * **Layout** — ``value_widget`` property provides the display widget
      for grid placement by ``_main.py``.

    For simple read-only ``QLabel`` components, subclasses need only
    override ``_get_display_text``. For custom widgets (editable
    ``QLineEdit``, etc.), override ``value_widget`` and
    ``_update_display`` as well.
    """

    #: If True, the value widget is placed below the label in vertical
    #: mode. Otherwise it sits beside it.
    _under_label_in_vertical: bool = False

    def __init__(
        self,
        parent_widget: QWidget,
    ) -> None:
        super().__init__(parent_widget)
        self._display_label = QLabel('', parent=parent_widget)
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

    # ------------------------------------------------------------------
    # Public API (consumed by _main.py / FileGeneralMetadata coordinator)
    # ------------------------------------------------------------------

    @property
    def value_widget(self) -> QWidget:
        """The primary display widget.  Override for non-QLabel components."""
        return self._display_label

    def load_entries(self, layer: Layer) -> None:
        """Update the display for *layer*."""
        self.value_widget.setToolTip(self._tooltip_text)
        self._update_display(layer)

    def bind_layer(self, layer: Layer) -> None:
        """Bind this component to *layer* and refresh its display."""
        self.load_entries(layer)

    def unbind_layer(self) -> None:
        """Clear any displayed state for an unbound component."""
        self.clear()

    def clear(self) -> None:
        """Reset the display to empty (no-layer state)."""
        self._display_label.setText('')

    def set_visible(self, visible: bool) -> None:
        """Show or hide both the header label and value widget for this component."""
        self.component_label.setVisible(visible)
        self.value_widget.setVisible(visible)

    # ------------------------------------------------------------------
    # Template methods
    # ------------------------------------------------------------------

    def _update_display(self, layer: Layer) -> None:
        """Update the display widget for *layer*.

        Default implementation sets the ``_display_label`` text via
        ``_get_display_text``.  Override for custom widget types.
        """
        self._display_label.setText(self._get_display_text(layer))

    @abstractmethod
    def _get_display_text(self, layer: Layer) -> str:
        """Return the display string for *layer*."""


class BoundFileComponentBase(BoundLayerOwner, FileComponentBase):
    """Template lifecycle for file components that need a bound layer."""

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)

    def bind_layer(self, layer: Layer) -> None:
        """Bind this interactive file component to *layer*."""
        if layer is self._selected_layer:
            FileComponentBase.bind_layer(self, layer)
            return
        if self._selected_layer is not None:
            self._disconnect_bound_layer_signals()
        self._bind_layer_reference(layer)
        self._connect_bound_layer_signals()
        FileComponentBase.bind_layer(self, layer)

    def unbind_layer(self) -> None:
        """Unbind this interactive file component and clear its display."""
        self._disconnect_bound_layer_signals()
        self._unbind_layer_reference()
        self._clear_bound_display()

    def clear(self) -> None:
        """Clear the display and unbind any active layer."""
        self.unbind_layer()

    def _clear_bound_display(self) -> None:
        """Clear the display widget for an unbound component."""
        FileComponentBase.clear(self)

    def _connect_bound_layer_signals(self) -> None:
        """Connect widget signals that require a bound layer."""

    def _disconnect_bound_layer_signals(self) -> None:
        """Disconnect widget signals that require a bound layer."""
