import polars as pl
import pytest
from logot import Logot, logged

from bfabric.experimental.upload_dataset import warn_on_trailing_spaces, polars_column_to_bfabric_type


def test_warn_on_trailing_spaces_when_no(logot: Logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b"], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_not_logged(logged.warning("%s"))


def test_warn_on_trailing_spaces_when_warning(logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b "], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_logged(logged.warning("Warning: Column 'b' contains trailing spaces."))


class TestPolarsColumnToBfabricType:
    @staticmethod
    @pytest.mark.parametrize("detect", [False, True])
    def test_basic_types(detect):
        df = pl.DataFrame({"str": ["a", "b"], "int": [1, 2], "int_as_str": ["1", "2"]})
        assert polars_column_to_bfabric_type(df, "str", detect_entity_reference=detect) == "String"
        assert polars_column_to_bfabric_type(df, "int", detect_entity_reference=detect) == "Integer"
        assert polars_column_to_bfabric_type(df, "int_as_str", detect_entity_reference=detect) == "String"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_int(entity_name):
        df = pl.DataFrame({entity_name: [1, 2]})
        assert polars_column_to_bfabric_type(df, entity_name, detect_entity_reference=True) == entity_name
        assert polars_column_to_bfabric_type(df, entity_name, detect_entity_reference=False) == "Integer"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_str(entity_name):
        df = pl.DataFrame({entity_name: ["1", "2"]})
        assert polars_column_to_bfabric_type(df, entity_name, detect_entity_reference=True) == entity_name
        assert polars_column_to_bfabric_type(df, entity_name, detect_entity_reference=False) == "String"
