import pytest

from bfabric_app_runner.cli.cmd_run import cmd_run_workunit


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="client")


@pytest.fixture
def mock_prepare(mocker):
    return mocker.patch("bfabric_app_runner.cli.cmd_run.cmd_prepare_workunit")


@pytest.fixture
def mock_workunit_definition(mocker):
    definition = mocker.MagicMock(name="workunit_definition")
    definition.registration.workunit_id = 54321
    definition.registration.application_id = 302
    definition.registration.application_name = "MaxQuant"
    return mocker.patch(
        "bfabric_app_runner.cli.cmd_run.WorkunitDefinition.from_ref",
        return_value=definition,
    )


@pytest.fixture
def subprocess_run(mocker):
    return mocker.patch("subprocess.run")


def _run(tmp_path, client):
    cmd_run_workunit(
        app_definition=tmp_path / "app.yml",
        scratch_root=tmp_path / "scratch",
        workunit_ref=54321,
        client=client,
    )


def _statuses(client):
    return [call.args[1]["status"] for call in client.save.call_args_list]


class TestCmdRunWorkunit:
    def test_make_failure_is_reported_without_a_traceback(
        self, tmp_path, mock_client, mock_prepare, mock_workunit_definition, subprocess_run, mocker, capsys
    ):
        """The inner process already reported the cause; this layer adds one line and no traceback."""
        subprocess_run.return_value = mocker.MagicMock(returncode=2)

        with pytest.raises(SystemExit) as exc_info:
            _run(tmp_path, mock_client)

        assert exc_info.value.code == 1
        stderr = capsys.readouterr().err
        assert stderr == "Error: Command failed with exit code 2: make run-all\n"
        assert "Traceback" not in stderr

    def test_make_failure_marks_the_workunit_failed(
        self, tmp_path, mock_client, mock_prepare, mock_workunit_definition, subprocess_run, mocker
    ):
        subprocess_run.return_value = mocker.MagicMock(returncode=2)

        with pytest.raises(SystemExit):
            _run(tmp_path, mock_client)

        assert _statuses(mock_client) == ["processing", "failed"]

    def test_success_marks_the_workunit_available(
        self, tmp_path, mock_client, mock_prepare, mock_workunit_definition, subprocess_run, mocker
    ):
        """Guards the ``check=False`` switch against silently swallowing a failure."""
        subprocess_run.return_value = mocker.MagicMock(returncode=0)

        _run(tmp_path, mock_client)

        assert _statuses(mock_client) == ["processing", "available"]
