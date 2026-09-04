import pytest
from bfabric import Bfabric
from bfabric_scripts.cli.api.delete import Params, cmd_api_delete


@pytest.fixture
def mock_client(mocker):
    client = mocker.MagicMock(spec=Bfabric)
    client.config.base_url = "http://test-bfabric.com/bfabric"
    return client


class TestDeleteNonInteractiveConfirmation:
    """Without a terminal the confirmation cannot be answered, so say what to pass instead of
    letting rich raise EOFError from a traceback."""

    def test_refuses_and_names_no_confirm(self, mocker, mock_client, capsys):
        mocker.patch("bfabric_scripts.cli.api.delete.is_interactive", return_value=False)
        params = Params(endpoint="resource", id=[42])

        cmd_api_delete(params, client=mock_client)

        mock_client.delete.assert_not_called()
        assert "--no-confirm" in capsys.readouterr().err

    def test_does_not_read_the_entities_first(self, mocker, mock_client):
        """The refusal is about the missing terminal, so it should not cost an API round-trip."""
        mocker.patch("bfabric_scripts.cli.api.delete.is_interactive", return_value=False)
        params = Params(endpoint="resource", id=[42])

        cmd_api_delete(params, client=mock_client)

        mock_client.read.assert_not_called()

    def test_no_confirm_still_deletes_without_a_terminal(self, mocker, mock_client):
        mocker.patch("bfabric_scripts.cli.api.delete.is_interactive", return_value=False)
        params = Params(endpoint="resource", id=[42], no_confirm=True)

        cmd_api_delete(params, client=mock_client)

        mock_client.delete.assert_called_once_with(endpoint="resource", id=[42])
