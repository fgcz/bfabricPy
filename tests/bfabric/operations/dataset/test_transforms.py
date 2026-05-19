import polars as pl
import pytest

from bfabric.operations.dataset._column_types import DatasetColumnTypes
from bfabric.operations.dataset.transforms import _polars_column_to_bfabric_type, polars_to_dataset_dict


@pytest.fixture
def column_types():
    return DatasetColumnTypes(entities={"Resource", "Dataset"})


class TestPolarsColumnToBfabricType:
    @staticmethod
    @pytest.mark.parametrize("detect", [False, True])
    def test_basic_types(detect, column_types):
        df = pl.DataFrame({"str": ["a", "b"], "int": [1, 2], "int_as_str": ["1", "2"]})
        ct = column_types if detect else None
        assert _polars_column_to_bfabric_type(df, "str", column_types=ct) == "String"
        assert _polars_column_to_bfabric_type(df, "int", column_types=ct) == "Integer"
        assert _polars_column_to_bfabric_type(df, "int_as_str", column_types=ct) == "String"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_int(entity_name, column_types):
        df = pl.DataFrame({entity_name: [1, 2]})
        assert _polars_column_to_bfabric_type(df, entity_name, column_types=column_types) == entity_name
        assert _polars_column_to_bfabric_type(df, entity_name, column_types=None) == "Integer"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_when_str(entity_name, column_types):
        df = pl.DataFrame({entity_name: ["1", "2"]})
        assert _polars_column_to_bfabric_type(df, entity_name, column_types=column_types) == entity_name
        assert _polars_column_to_bfabric_type(df, entity_name, column_types=None) == "String"

    @staticmethod
    def test_entity_reference_when_not_actually_a_reference(column_types):
        df = pl.DataFrame({"Dataset": ["1", "2"], "Resource": ["3", "a"]})
        assert _polars_column_to_bfabric_type(df, "Dataset", column_types=column_types) == "Dataset"
        assert _polars_column_to_bfabric_type(df, "Resource", column_types=column_types) == "String"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_lowercase_when_int(entity_name, column_types):
        lowercase_name = entity_name.lower()
        df = pl.DataFrame({lowercase_name: [1, 2]})
        assert _polars_column_to_bfabric_type(df, lowercase_name, column_types=column_types) == entity_name
        assert _polars_column_to_bfabric_type(df, lowercase_name, column_types=None) == "Integer"

    @staticmethod
    @pytest.mark.parametrize("entity_name", ["Resource", "Dataset"])
    def test_entity_reference_lowercase_when_str(entity_name, column_types):
        lowercase_name = entity_name.lower()
        df = pl.DataFrame({lowercase_name: ["1", "2"]})
        assert _polars_column_to_bfabric_type(df, lowercase_name, column_types=column_types) == entity_name
        assert _polars_column_to_bfabric_type(df, lowercase_name, column_types=None) == "String"

    @staticmethod
    def test_entity_reference_lowercase_when_not_actually_a_reference(column_types):
        df = pl.DataFrame({"dataset": ["1", "2"], "resource": ["3", "a"]})
        assert _polars_column_to_bfabric_type(df, "dataset", column_types=column_types) == "Dataset"
        assert _polars_column_to_bfabric_type(df, "resource", column_types=column_types) == "String"

    @staticmethod
    @pytest.mark.parametrize(
        "column_name,expected_entity",
        [
            ("rEsOuRcE", "Resource"),
            ("dAtAsEt", "Dataset"),
            ("RESOURCE", "Resource"),
            ("DATASET", "Dataset"),
        ],
    )
    def test_entity_reference_mixed_case_when_int(column_name, expected_entity, column_types):
        df = pl.DataFrame({column_name: [1, 2]})
        assert _polars_column_to_bfabric_type(df, column_name, column_types=column_types) == expected_entity
        assert _polars_column_to_bfabric_type(df, column_name, column_types=None) == "Integer"

    @staticmethod
    def test_non_entity_lowercase_column_name(column_types):
        df = pl.DataFrame({"some_column": [1, 2], "another_col": ["a", "b"]})
        assert _polars_column_to_bfabric_type(df, "some_column", column_types=column_types) == "Integer"
        assert _polars_column_to_bfabric_type(df, "another_col", column_types=column_types) == "String"


def test_polars_to_dataset_dict_shape():
    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    result = polars_to_dataset_dict(df)
    assert set(result.keys()) == {"attribute", "item"}
    attrs = result["attribute"]
    assert [a["name"] for a in attrs] == ["a", "b"]
    assert [a["position"] for a in attrs] == [1, 2]
    assert attrs[0]["type"] == "Integer"
    assert attrs[1]["type"] == "String"

    items = result["item"]
    assert len(items) == 2
    assert items[0]["position"] == 1
    assert items[0]["field"] == [
        {"attributeposition": 1, "value": 1},
        {"attributeposition": 2, "value": "x"},
    ]
