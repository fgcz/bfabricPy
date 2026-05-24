from unittest.mock import MagicMock

import pytest
import polars as pl
import polars.testing
from pathlib import Path

from bfabric.results.result_container import ResultContainer
from bfabric_app_runner.output_registration.annotation_table import generate_output_table
from bfabric_app_runner.output_registration.register import RegisterAllOutputs, _save_annotations
from bfabric_app_runner.specs.outputs.annotations import BfabricOutputDataset, IncludeDatasetRef, IncludeResourceRef


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
                    "Anchor": [None, "#example", ""],
                    "My custom column": ["value1", "value2", None],
                    "prop": [None, None, "value"],
                }
            ),
        )


class TestSaveAnnotations:
    @pytest.fixture()
    def mock_client(self) -> MagicMock:
        client = MagicMock()
        client.config.base_url = "https://example.bfabric"
        client.save.return_value = ResultContainer(results=[{"id": 999}], total_pages_api=None, errors=[])
        return client

    @pytest.fixture()
    def mock_workunit_definition(self) -> MagicMock:
        mock = MagicMock()
        mock.registration.workunit_id = 42
        mock.registration.container_id = 7
        return mock

    @pytest.fixture()
    def outputs(self) -> RegisterAllOutputs:
        return RegisterAllOutputs(resources_mapping={Path("custom.txt"): 300})

    def test_creates_dataset_with_default_name(self, mock_client, mock_workunit_definition, outputs):
        annotation = BfabricOutputDataset(
            type="bfabric_output_dataset",
            include_resources=[IncludeResourceRef(store_entry_path="custom.txt", metadata={"prop": "value"})],
        )
        _save_annotations(outputs, [annotation], client=mock_client, workunit_definition=mock_workunit_definition)
        mock_client.save.assert_called_once()
        endpoint, payload = mock_client.save.call_args[0]
        assert endpoint == "dataset"
        assert payload["name"] == "Output Dataset (workunit 42)"
        assert payload["containerid"] == 7
        assert payload["workunitid"] == 42

    def test_uses_explicit_name(self, mock_client, mock_workunit_definition, outputs):
        annotation = BfabricOutputDataset(
            type="bfabric_output_dataset",
            name="My Results",
            include_resources=[IncludeResourceRef(store_entry_path="custom.txt")],
        )
        _save_annotations(outputs, [annotation], client=mock_client, workunit_definition=mock_workunit_definition)
        assert mock_client.save.call_args[0][1]["name"] == "My Results"

    def test_no_annotations_no_save(self, mock_client, mock_workunit_definition, outputs):
        _save_annotations(outputs, [], client=mock_client, workunit_definition=mock_workunit_definition)
        mock_client.save.assert_not_called()
