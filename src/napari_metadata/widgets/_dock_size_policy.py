"""Shared handling of napari's dock-widget vertical size-policy clamp.

napari 0.9.0 (napari/napari#9393) forces the widget inside every dock to
``(Preferred, Maximum)``, which turns its size hint into a hard height
ceiling: the dock can no longer be stretched taller (docked or floating) and
expanded content gets no room to open.  Both top-level dock widgets
(``MetadataWidget`` and ``ViewerMetadataWidget``) call
:func:`restore_dock_size_policy` from their ``showEvent`` so the ``Expanding``
policy each widget is created with is re-asserted after napari has clobbered
it.

The guard (only act when the vertical policy is ``Maximum``) is what keeps this
compatible with the upstream fix, napari/napari#9462 (targeted at 0.9.1): there
the clamp is only applied to widgets that do *not* ask for vertical space, so a
growable widget like these is left untouched and this shim becomes a no-op.
The whole module can be deleted once napari >= 0.9.1 is the minimum supported
version.
"""

from __future__ import annotations

from qtpy.QtWidgets import QSizePolicy, QWidget


def restore_dock_size_policy(widget: QWidget) -> None:
    """Undo napari 0.9.0's dock clamp on *widget*, if it has been applied.

    napari/napari#9393 applies its ``(Preferred, Maximum)`` clamp when a widget is
    added to a dock (before the widget is first shown).  Top-level dock widgets
    call this from their ``showEvent`` to re-assert the ``Expanding`` policy
    they declare at construction.

    It only acts when the vertical policy is ``Maximum`` — the signature of the
    0.9.0 clamp — so it is a no-op after release of napari/napari#9462,
    where growable widgets keep their own policy (see the module docstring).
    """
    if widget.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum:
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
