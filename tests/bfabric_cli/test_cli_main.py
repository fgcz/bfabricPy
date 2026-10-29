import pytest

from bfabric_scripts.cli import __main__ as cli_main


def test_main_reports_a_command_error_in_one_line(mocker, capsys):
    """Commands without ``@use_client`` (e.g. ``auth``) share the same one-line error boundary."""
    mocker.patch.object(cli_main, "setup_script_logging")
    mocker.patch.object(cli_main, "app", side_effect=ValueError("base URL must end in /bfabric"))

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code == 1
    assert capsys.readouterr().err == "Error: base URL must end in /bfabric\n"
