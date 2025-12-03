import pytest
import polars as pl
import polars.testing
from pathlib import Path
from bfabric_app_runner.specs.outputs.annotations import BfabricOutputDataset, IncludeDatasetRef, IncludeResourceRef
from bfabric_app_runner.output_registration.annotation_table import generate_output_table


class TestGenerateOutputTable:
    @pytest.fixture
    def input_table_path(self, tmp_path):
        table = pl.DataFrame(
            {"Resource": [100, 200], "Anchor": [None, "#example"], "My custom column": ["value1", "value2"]}
        )
        path = tmp_path / "input" / "table.parquet"
        path.parent.mkdir()
        table.write_parquet(path)
        return path

    @pytest.fixture()
    def spec(self, input_table_path):
        return BfabricOutputDataset(
            type="bfabric_output_dataset",
            include_tables=[IncludeDatasetRef(local_path=input_table_path)],
            include_resources=[IncludeResourceRef(store_entry_path="custom.txt", metadata={"prop": "value"})],
        )

    @pytest.fixture()
    def resource_mapping(self) -> dict[Path, int]:
        return {Path("custom.txt"): 300}

    def test_generate_output_table(self, spec, resource_mapping):
        table = generate_output_table(spec, resource_mapping)
        assert table.columns == ["Resource", "Anchor", "My custom column", "prop"]
        polars.testing.assert_frame_equal(
            table,
            pl.DataFrame(
                {
                    "Resource": [100, 200, 300],
                    "Anchor": [None, "#example", None],
                    "My custom column": ["value1", "value2", None],
                    "prop": [None, None, "value"],
                }
            ),
        )
