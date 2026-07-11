"""Shared layout utilities for napari-metadata widgets.

``_allocate_section_extents`` is used by both the layer-metadata and
viewer-metadata top-level widgets to distribute available space across
collapsible sections using a water-filling strategy.
"""

from __future__ import annotations


def _allocate_section_extents(
    *,
    expanded: list[bool],
    collapsed_extents: list[int],
    preferred_extents: list[int],
    available: int,
    spacing: int,
) -> list[int]:
    """Distribute available pixels across collapsed and expanded sections.

    Collapsed sections always keep their collapsed extent. Expanded sections
    share the remaining pixels with a water-filling strategy so smaller
    preferred extents are satisfied first.

    Parameters
    ----------
    expanded : list[bool]
        Whether each section is expanded.
    collapsed_extents : list[int]
        Minimum pixel extent (height or width) per section when collapsed.
    preferred_extents : list[int]
        Desired pixel extent per section when expanded.
    available : int
        Total pixel extent available for all sections.
    spacing : int
        Total pixel gap between all sections.

    Returns
    -------
    list[int]
        Allocated pixel extent for each section.
    """
    extents = collapsed_extents.copy()
    expanded_indices = [
        index for index, is_expanded in enumerate(expanded) if is_expanded
    ]
    if not expanded_indices:
        return extents

    collapsed_total = sum(
        extent
        for extent, is_expanded in zip(
            collapsed_extents, expanded, strict=True
        )
        if not is_expanded
    )
    usable = max(available - spacing - collapsed_total, 0)

    preferred_by_index = {
        index: max(preferred_extents[index], collapsed_extents[index])
        for index in expanded_indices
    }
    minimum_total = sum(collapsed_extents[index] for index in expanded_indices)
    if usable <= minimum_total:
        return extents

    preferred_total = sum(
        preferred_by_index[index] for index in expanded_indices
    )
    if usable >= preferred_total:
        for index in expanded_indices:
            extents[index] = preferred_by_index[index]
        return extents

    remaining = usable
    for offset, index in enumerate(
        sorted(expanded_indices, key=lambda item: preferred_by_index[item])
    ):
        share = remaining // (len(expanded_indices) - offset)
        extent = max(
            collapsed_extents[index],
            min(preferred_by_index[index], share),
        )
        extents[index] = extent
        remaining -= extent

    return extents
