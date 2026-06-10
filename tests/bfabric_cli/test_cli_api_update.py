import json

import pytest
from bfabric import Bfabric
from bfabric.results.result_container import ResultContainer
from bfabric_scripts.cli.api.update import Params, cmd_api_update
from bfabric_scripts.cli.api.output_format import OutputFormat


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Bfabric)
    client.config.base_url = "http://test-bfabric.com"
    return client


@pytest.fixture
def save_result():
    return ResultContainer(
        [{"id": 42, "name": "Test Workunit", "status": "AVAILABLE"}],
        total_pages_api=1,
        errors=[],
    )


class TestUpdateOutputFormat:
    def test_default_format_is_json(self):
        params = Params(endpoint="workunit", entity_id=42, attributes=[("status", "available")])
        assert params.format == OutputFormat.JSON

    def test_update_emits_valid_json_by_default(self, mock_client, save_result, capsys):
        # Arrange — reproduces the exact scenario from issue #503
        mock_client.save.return_value = save_result
        params = Params(
            endpoint="workunit",
            entity_id=42,
            attributes=[("status", "available")],
            no_confirm=True,
        )

        # Act
        cmd_api_update(params, client=mock_client)

        # Assert — output must be parseable JSON (the bug was Python repr with single quotes)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert isinstance(parsed, list)
        assert parsed[0]["id"] == 42

    def test_update_format_json_explicit(self, mock_client, save_result, capsys):
        mock_client.save.return_value = save_result
        params = Params(
            endpoint="workunit",
            entity_id=42,
            attributes=[("status", "available")],
            no_confirm=True,
            format=OutputFormat.JSON,
        )

        cmd_api_update(params, client=mock_client)

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed[0]["status"] == "AVAILABLE"

    def test_update_format_yaml(self, mock_client, save_result, capsys):
        import yaml

        mock_client.save.return_value = save_result
        params = Params(
            endpoint="workunit",
            entity_id=42,
            attributes=[("status", "available")],
            no_confirm=True,
            format=OutputFormat.YAML,
        )

        cmd_api_update(params, client=mock_client)

        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert isinstance(parsed, list)
        assert parsed[0]["id"] == 42

    def test_update_passes_correct_args_to_save(self, mock_client, save_result):
        mock_client.save.return_value = save_result
        params = Params(
            endpoint="workunit",
            entity_id=42,
            attributes=[("status", "available")],
            no_confirm=True,
        )

        cmd_api_update(params, client=mock_client)

        mock_client.save.assert_called_once_with("workunit", {"id": 42, "status": "available"})
