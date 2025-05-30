import pytest
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,
    SlurmWorkunitSpecialStrings,
)


class TestSlurmWorkunitSpecialStrings:
    """Test the special strings enum."""

    def test_parse_default(self):
        result = SlurmWorkunitSpecialStrings.parse("[default]")
        assert result == SlurmWorkunitSpecialStrings.default

    def test_parse_auto(self):
        result = SlurmWorkunitSpecialStrings.parse("[auto]")
        assert result == SlurmWorkunitSpecialStrings.auto

    def test_parse_unknown_returns_none(self):
        result = SlurmWorkunitSpecialStrings.parse("unknown")
        assert result is None

    def test_parse_empty_string_returns_none(self):
        result = SlurmWorkunitSpecialStrings.parse("")
        assert result is None


class TestSlurmWorkunitParams:
    """Test the SlurmWorkunitParams class."""

    def test_default_values(self):
        """Test that all fields default to [default] special string."""
        params = SlurmWorkunitParams()
        assert params.partition == SlurmWorkunitSpecialStrings.default
        assert params.nodelist == SlurmWorkunitSpecialStrings.default
        assert params.mem == SlurmWorkunitSpecialStrings.default
        assert params.time == SlurmWorkunitSpecialStrings.default

    def test_string_values(self):
        """Test setting string values directly."""
        params = SlurmWorkunitParams(partition="compute", nodelist="node001", mem="8G", time="01:30:00")
        assert params.partition == "compute"
        assert params.nodelist == "node001"
        assert params.mem == "8G"
        assert params.time == "01:30:00"

    def test_special_string_parsing(self):
        """Test that special strings are parsed correctly."""
        params = SlurmWorkunitParams(partition="[auto]", nodelist="[default]", mem="4G", time="[auto]")
        assert params.partition == SlurmWorkunitSpecialStrings.auto
        assert params.nodelist == SlurmWorkunitSpecialStrings.default
        assert params.mem == "4G"
        assert params.time == SlurmWorkunitSpecialStrings.auto

    def test_field_aliases(self):
        """Test that field aliases work correctly."""
        # Test with -- prefixed aliases
        params1 = SlurmWorkunitParams(**{"--partition": "compute", "--mem": "8G"})
        assert params1.partition == "compute"
        assert params1.mem == "8G"

        # Test with regular field names
        params2 = SlurmWorkunitParams(**{"partition": "gpu", "time": "02:00:00"})
        assert params2.partition == "gpu"
        assert params2.time == "02:00:00"

    def test_get_field_with_string_values(self):
        """Test _get_field returns string values as-is."""
        params = SlurmWorkunitParams(partition="compute", mem="8G")
        assert params._get_field("partition") == "compute"
        assert params._get_field("mem") == "8G"

    def test_get_field_with_default_returns_none(self):
        """Test _get_field returns None for default special strings."""
        params = SlurmWorkunitParams()  # All defaults
        assert params._get_field("partition") is None
        assert params._get_field("nodelist") is None
        assert params._get_field("mem") is None
        assert params._get_field("time") is None

    def test_get_field_with_auto_raises_not_implemented(self):
        """Test _get_field raises NotImplementedError for auto special strings."""
        params = SlurmWorkunitParams(partition="[auto]")
        with pytest.raises(NotImplementedError, match="Currently unsupported value for partition"):
            params._get_field("partition")

    def test_as_dict_with_defaults_returns_empty(self):
        """Test as_dict returns empty dict when all values are default."""
        params = SlurmWorkunitParams()
        result = params.as_dict()
        assert result == {}

    def test_as_dict_with_string_values(self):
        """Test as_dict returns correct mapping for string values."""
        params = SlurmWorkunitParams(partition="compute", nodelist="node001,node002", mem="16G", time="03:00:00")
        result = params.as_dict()
        expected = {"--partition": "compute", "--nodelist": "node001,node002", "--mem": "16G", "--time": "03:00:00"}
        assert result == expected

    def test_as_dict_mixed_values(self):
        """Test as_dict with mix of defaults and string values."""
        params = SlurmWorkunitParams(
            partition="compute",
            # nodelist defaults to [default]
            mem="8G",
            # time defaults to [default]
        )
        result = params.as_dict()
        expected = {"--partition": "compute", "--mem": "8G"}
        assert result == expected

    def test_as_dict_with_auto_raises_error(self):
        """Test as_dict raises error when encountering [auto] values."""
        params = SlurmWorkunitParams(partition="[auto]")
        with pytest.raises(NotImplementedError):
            params.as_dict()

    def test_validate_special_string_method(self):
        """Test the _parse_string class method directly."""
        # String input
        assert SlurmWorkunitParams._parse_string("regular_string") == "regular_string"

        # Special string input
        assert SlurmWorkunitParams._parse_string("[default]") == SlurmWorkunitSpecialStrings.default
        assert SlurmWorkunitParams._parse_string("[auto]") == SlurmWorkunitSpecialStrings.auto

        # Enum input (should pass through)
        assert (
            SlurmWorkunitParams._parse_string(SlurmWorkunitSpecialStrings.default)
            == SlurmWorkunitSpecialStrings.default
        )

    def test_complex_scenario(self):
        """Test a realistic scenario with mixed field types."""
        # Simulate data that might come from a workunit
        workunit_data = {
            "--partition": "gpu-compute",
            "mem": "[default]",  # Will use system default
            "--time": "24:00:00",
            "nodelist": "[default]",  # Will use system default
        }

        params = SlurmWorkunitParams(**workunit_data)

        # Check parsed values
        assert params.partition == "gpu-compute"
        assert params.mem == SlurmWorkunitSpecialStrings.default
        assert params.time == "24:00:00"
        assert params.nodelist == SlurmWorkunitSpecialStrings.default

        # Check as_dict output (only non-default values)
        result = params.as_dict()
        expected = {"--partition": "gpu-compute", "--time": "24:00:00"}
        assert result == expected
