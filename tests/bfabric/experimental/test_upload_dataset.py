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


@pytest.fixture
def column_types(mocker):
    return mocker.Mock(name="column_types", entities=["Resource", "Dataset"])


class TestPolarsColumnToBfabricType:
    @staticmethod
    @pytest.mark.parametrize("detect", [False, True])
    def test_basic_types(detect, column_types):
        df = pl.DataFrame({"str": ["a", "b"], "int": [1, 2], "int_as_str": ["1", "2"]})
        column_types = column_types if detect else None
        assert polars_column_to_bfabric_type(df, "str", column_types=column_types) == "String"
        assert polars_column_to_bfabric_type(df, "int", column_types=column_types) == "Integer"
        assert polars_column_to_bfabric_type(df, "int_as_str", column_types=column_types) == "String"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_int(entity_name, column_types):
        df = pl.DataFrame({entity_name: [1, 2]})
        assert polars_column_to_bfabric_type(df, entity_name, column_types=column_types) == entity_name
        assert polars_column_to_bfabric_type(df, entity_name, column_types=None) == "Integer"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_str(entity_name, column_types):
        df = pl.DataFrame({entity_name: ["1", "2"]})
        assert polars_column_to_bfabric_type(df, entity_name, column_types=column_types) == entity_name
        assert polars_column_to_bfabric_type(df, entity_name, column_types=None) == "String"
