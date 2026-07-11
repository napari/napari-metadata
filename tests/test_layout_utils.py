"""Tests for the ``_allocate_section_extents`` layout utility.

These tests verify the water-filling distribution algorithm used by both
the layer-metadata and viewer-metadata top-level widgets.
"""

from __future__ import annotations

from napari_metadata._layout_utils import _allocate_section_extents


class TestAllocateSectionExtents:
    def test_collapsed_sections_keep_collapsed_extents(self):
        extents = _allocate_section_extents(
            expanded=[False, False],
            collapsed_extents=[10, 20],
            preferred_extents=[50, 60],
            available=100,
            spacing=4,
        )

        assert extents == [10, 20]

    def test_expanded_sections_use_collapsed_extents_when_space_is_tight(self):
        extents = _allocate_section_extents(
            expanded=[True, True],
            collapsed_extents=[10, 10],
            preferred_extents=[30, 40],
            available=24,
            spacing=4,
        )

        assert extents == [10, 10]

    def test_expanded_sections_use_preferred_extents_when_space_is_plentiful(
        self,
    ):
        extents = _allocate_section_extents(
            expanded=[True, True],
            collapsed_extents=[10, 10],
            preferred_extents=[30, 40],
            available=100,
            spacing=4,
        )

        assert extents == [30, 40]

    def test_expanded_sections_water_fill_partial_space(self):
        extents = _allocate_section_extents(
            expanded=[True, True],
            collapsed_extents=[10, 10],
            preferred_extents=[20, 50],
            available=64,
            spacing=4,
        )

        assert extents == [20, 40]

    def test_preferred_extents_are_never_smaller_than_collapsed_extents(self):
        extents = _allocate_section_extents(
            expanded=[True, False, True],
            collapsed_extents=[12, 9, 15],
            preferred_extents=[8, 50, 10],
            available=80,
            spacing=6,
        )

        assert extents == [12, 9, 15]

    def test_mixed_expanded_and_collapsed_with_limited_space(self):
        extents = _allocate_section_extents(
            expanded=[False, True, True],
            collapsed_extents=[10, 10, 10],
            preferred_extents=[50, 30, 40],
            available=64,
            spacing=4,
        )

        # Water-fill: 50 usable px shared between 2 expanded sections
        assert extents == [10, 25, 25]
