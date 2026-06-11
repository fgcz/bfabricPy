"""Tests for the shared output_format module (issue #503 fix)."""

import datetime
import decimal
import json

import pytest
from bfabric_scripts.cli.api.output_format import OutputFormat, _determine_output_columns, render_output


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock()
    client.config.base_url = "http://test-bfabric.com"
    return client


@pytest.fixture
def sample_results():
    return [
        {"id": 1, "name": "Alpha"},
        {"id": 2, "name": "Beta"},
    ]


class TestRenderOutputJsonSafety:
    """Ensure JSON output survives non-JSON-native values (Zeep engine produces these)."""

    def test_datetime_values_are_serialised(self, mock_client, mocker):
        results = [{"id": 1, "created": datetime.datetime(2024, 1, 1, 12, 0, 0)}]
        output = render_output(
            results,
            output_format=OutputFormat.JSON,
            endpoint="workunit",
            client=mock_client,
            console=mocker.Mock(),
        )
        parsed = json.loads(output)
        # The datetime should be serialised to a string (default=str)
        assert isinstance(parsed[0]["created"], str)

    def test_decimal_values_are_serialised(self, mock_client, mocker):
        results = [{"id": 1, "amount": decimal.Decimal("3.14")}]
        output = render_output(
            results,
            output_format=OutputFormat.JSON,
            endpoint="workunit",
            client=mock_client,
            console=mocker.Mock(),
        )
        parsed = json.loads(output)
        assert parsed[0]["amount"] == "3.14"

    def test_plain_dict_roundtrips(self, mock_client, sample_results, mocker):
        output = render_output(
            sample_results,
            output_format=OutputFormat.JSON,
            endpoint="resource",
            client=mock_client,
            console=mocker.Mock(),
        )
        parsed = json.loads(output)
        assert parsed == sample_results


class TestDetermineOutputColumnsMaxColumnsNone:
    def test_none_max_columns_returns_all_available(self):
        results = [{"id": 1, "name": "x", "status": "y", "type": "z"}]
        columns = _determine_output_columns(results=results, columns=None, max_columns=None)
        assert set(columns) == {"id", "name", "status", "type"}

    def test_zero_max_columns_raises(self):
        with pytest.raises(ValueError, match="max_columns must be at least 1"):
            _determine_output_columns(results=[{"id": 1}], columns=None, max_columns=0)
