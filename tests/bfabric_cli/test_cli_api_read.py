import json
from pathlib import Path

import pytest
import yaml
from bfabric import Bfabric
from bfabric.results.result_container import ResultContainer
from bfabric_scripts.cli.api.cli_api_read import (
    Params,
    OutputFormat,
    perform_query,
    read,
    render_output,
    _determine_output_columns,
)
from rich.console import Console


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Bfabric)
    client.config.base_url = "http://test-bfabric.com"
    return client


@pytest.fixture
def mock_console(mocker):
    return mocker.Mock(spec=Console)


@pytest.fixture
def sample_results():
    return [
        {"id": 1, "name": "Sample 1", "status": "active", "groupingvar": {"name": "Group A"}},
        {"id": 2, "name": "Sample 2", "status": "inactive", "groupingvar": {"name": "Group B"}},
    ]


class TestPerformQuery:
    def test_perform_query_basic(self, mock_client, mock_console):
        # Arrange
        params = Params(endpoint="resource", query=[("status", "active")])
        mock_client.read.return_value = ResultContainer([{"id": 1, "name": "Test"}])

        # Act
        results = perform_query(params, mock_client, mock_console)

        # Assert
        mock_client.read.assert_called_once_with(endpoint="resource", obj={"status": "active"}, max_results=100)
        assert len(results) == 1
        assert results[0]["id"] == 1

    def test_perform_query_multiple_values(self, mock_client, mock_console):
        # Arrange
        params = Params(
            endpoint="resource", query=[("status", "active"), ("status", "pending")], columns=["id"], limit=10
        )
        mock_client.read.return_value = ResultContainer([{"id": 1, "status": "active"}, {"id": 2, "status": "pending"}])

        # Act
        results = perform_query(params, mock_client, mock_console)

        # Assert
        mock_client.read.assert_called_once_with(
            endpoint="resource", obj={"status": ["active", "pending"]}, max_results=10
        )
        assert len(results) == 2


class TestRenderOutput:
    def test_render_json_output(self, mocker, sample_results):
        # Arrange
        params = Params(endpoint="resource", columns=["id", "name"], format=OutputFormat.JSON)

        # Act
        output = render_output(sample_results, params, mocker.Mock(), mocker.Mock())

        # Assert
        parsed = json.loads(output)
        assert len(parsed) == 2
        assert all(set(item.keys()) == {"id", "name"} for item in parsed)

    def test_render_yaml_output(self, mocker, sample_results):
        # Arrange
        params = Params(endpoint="resource", columns=["id", "name"], format=OutputFormat.YAML)

        # Act
        output = render_output(sample_results, params, mocker.Mock(), mocker.Mock())

        # Assert
        parsed = yaml.safe_load(output)
        assert len(parsed) == 2
        assert all(set(item.keys()) == {"id", "name"} for item in parsed)

    def test_render_tsv_output(self, sample_results, mocker):
        # Arrange
        params = Params(endpoint="resource", columns=["id", "name"], format=OutputFormat.TSV)
        mock_flatten = mocker.patch("bfabric_scripts.cli.api.cli_api_read.flatten_relations")
        mock_df = mocker.Mock()
        mock_flatten.return_value = mock_df

        # Act
        render_output(sample_results, params, mocker.Mock(), mocker.Mock())

        # Assert
        mock_flatten.assert_called_once()
        mock_df.write_csv.assert_called_once_with(separator="\t")


class TestDetermineOutputColumns:
    def test_determine_output_columns_with_specified_columns(self):
        # Arrange
        results = [{"id": 1, "name": "Test", "status": "active"}]
        specified_columns = ["id", "name"]

        # Act
        columns = _determine_output_columns(
            results=results, columns=specified_columns, max_columns=7, output_format=OutputFormat.TABLE_RICH
        )

        # Assert
        assert columns == ["id", "name"]

    def test_determine_output_columns_with_max_columns(self):
        # Arrange
        results = [{"id": 1, "name": "Test", "status": "active", "type": "sample"}]

        # Act
        columns = _determine_output_columns(
            results=results, columns=None, max_columns=2, output_format=OutputFormat.TABLE_RICH
        )

        # Assert
        assert len(columns) == 3  # id + 2 more columns
        assert "id" in columns

    def test_determine_output_columns_invalid_max_columns(self):
        # Arrange
        results = [{"id": 1, "name": "Test"}]

        # Act/Assert
        with pytest.raises(ValueError, match="max_columns must be at least 1"):
            _determine_output_columns(
                results=results, columns=None, max_columns=0, output_format=OutputFormat.TABLE_RICH
            )


class TestReadFunction:
    def test_read_json_output(self, mock_client, mock_console, sample_results, mocker):
        # Arrange
        mock_perform_query = mocker.patch("bfabric_scripts.cli.api.cli_api_read.perform_query")
        mock_perform_query.return_value = sample_results

        params = Params(
            endpoint="resource", columns=["id", "name"], format=OutputFormat.JSON, query=[("status", "active")]
        )

        # Act
        result = read(params, client=mock_client)

        # Assert
        mock_perform_query.assert_called_once_with(params=params, client=mock_client, console_user=mocker.ANY)
        assert result is None  # Function should return None on success

    def test_read_with_file_output(self, mock_client, mock_console, sample_results, mocker, tmp_path):
        # Arrange
        output_file = tmp_path / "test_output.json"
        mock_perform_query = mocker.patch("bfabric_scripts.cli.api.cli_api_read.perform_query")
        mock_perform_query.return_value = sample_results

        params = Params(
            endpoint="resource",
            columns=["id", "name"],
            format=OutputFormat.JSON,
            query=[("status", "active")],
            file=output_file,
        )

        # Act
        result = read(params, client=mock_client)

        # Assert
        assert result is None
        assert output_file.exists()
        content = output_file.read_text()
        parsed_content = json.loads(content)
        assert len(parsed_content) == len(sample_results)
        assert all(set(item.keys()) == {"id", "name"} for item in parsed_content)

    def test_read_with_tsv_format(self, mock_client, mock_console, sample_results, mocker):
        # Arrange
        mock_perform_query = mocker.patch("bfabric_scripts.cli.api.cli_api_read.perform_query")
        mock_perform_query.return_value = sample_results
        mock_flatten = mocker.patch("bfabric_scripts.cli.api.cli_api_read.flatten_relations")
        mock_df = mocker.Mock()
        mock_df.write_csv.return_value = "mocked,csv,content"
        mock_flatten.return_value = mock_df

        params = Params(
            endpoint="resource", columns=["id", "name"], format=OutputFormat.TSV, query=[("status", "active")]
        )

        # Act
        result = read(params, client=mock_client)

        # Assert
        mock_perform_query.assert_called_once()
        mock_flatten.assert_called_once()
        mock_df.write_csv.assert_called_once_with(separator="\t")
        assert result is None

    def test_read_with_invalid_file_output(self, mock_client, mock_console, sample_results, mocker):
        # Arrange
        mock_perform_query = mocker.patch("bfabric_scripts.cli.api.cli_api_read.perform_query")
        mock_perform_query.return_value = sample_results

        # Using TABLE_RICH format which doesn't support file output
        params = Params(
            endpoint="resource",
            columns=["id", "name"],
            format=OutputFormat.TABLE_RICH,
            query=[("status", "active")],
            file=Path("test_output.txt"),
        )

        # Act
        result = read(params, client=mock_client)

        # Assert
        assert result == 1  # Should return error code 1
