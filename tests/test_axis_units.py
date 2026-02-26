"""Tests for _UnitConfig and AxisType."""

import pint
import pytest

from napari_metadata._axis_units import AxisType, _UnitConfig


class TestUnitConfig:
    """_UnitConfig encapsulates the curated unit list and default for an axis."""

    def test_pint_units_returns_pint_unit_objects(self):
        unit_cfg = AxisType.SPACE.value
        units = unit_cfg.pint_units()
        assert len(units) == len(unit_cfg.units)
        for u in units:
            assert isinstance(u, pint.Unit)

    def test_pint_units_match_configured_strings(self):
        unit_cfg = AxisType.TIME.value
        unit_strs = [str(u) for u in unit_cfg.pint_units()]
        for name in unit_cfg.units:
            assert name in unit_strs

    def test_default_is_in_units(self):
        """The default unit must be one of the configured units."""
        for at in AxisType:
            if at.value is not None:
                assert at.value.default in at.value.units

    def test_frozen(self):
        """_UnitConfig is immutable."""
        unit_cfg = AxisType.SPACE.value
        with pytest.raises((AttributeError, TypeError)):
            unit_cfg.default = 'meter'  # type: ignore[misc]


class TestAxisType:
    def test_members(self):
        names = AxisType.names()
        assert "space" in names
        assert "time" in names
        assert "string" in names

    def test_str(self):
        assert str(AxisType.SPACE) == "space"
        assert str(AxisType.TIME) == "time"
        assert str(AxisType.STRING) == "string"

    def test_from_name_valid(self):
        assert AxisType.from_name("space") is AxisType.SPACE
        assert AxisType.from_name("time") is AxisType.TIME
        assert AxisType.from_name("string") is AxisType.STRING

    def test_from_name_invalid(self):
        assert AxisType.from_name("nonexistent") is None

    def test_names_returns_all_members(self):
        assert len(AxisType.names()) == len(list(AxisType))

    def test_space_has_unit_config(self):
        assert isinstance(AxisType.SPACE.value, _UnitConfig)

    def test_time_has_unit_config(self):
        assert isinstance(AxisType.TIME.value, _UnitConfig)

    def test_string_has_no_config(self):
        assert AxisType.STRING.value is None

    def test_space_units_contain_expected(self):
        units = AxisType.SPACE.value.units
        assert "pixel" in units
        assert "micrometer" in units
        assert "meter" in units
        assert "none" not in units

    def test_time_units_contain_expected(self):
        units = AxisType.TIME.value.units
        assert "second" in units
        assert "millisecond" in units
        assert "hour" in units
        assert "none" not in units

    def test_space_default_unit(self):
        assert AxisType.SPACE.value.default == "pixel"

    def test_time_default_unit(self):
        assert AxisType.TIME.value.default == "second"

    @pytest.mark.parametrize(
        "axis_type",
        list(AxisType),
        ids=[str(a) for a in AxisType],
    )
    def test_value_is_config_or_none(self, axis_type):
        """Every AxisType member has either a _UnitConfig or None."""
        assert axis_type.value is None or isinstance(axis_type.value, _UnitConfig)
