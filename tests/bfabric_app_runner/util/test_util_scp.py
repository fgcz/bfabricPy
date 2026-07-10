from __future__ import annotations

import pytest

from bfabric_app_runner.util.scp import scp


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


def test_scp_quotes_remote_mkdir_path(mocker, mock_subprocess):
    # ssh runs its trailing args through the remote shell, so a directory containing shell
    # metacharacters must be quoted -- otherwise it would execute arbitrary commands on the host.
    scp(source="/local/file.txt", target="host:/remote/$(touch pwned)/file.txt")

    ssh_call = mock_subprocess.call_args_list[0]
    assert ssh_call == mocker.call(["ssh", "host", "mkdir", "-p", "'/remote/$(touch pwned)'"], check=True)


def test_scp_rejects_option_like_target(mock_subprocess):
    # A target beginning with '-' would be parsed by scp/ssh as an option (e.g. -oProxyCommand=...),
    # smuggling local command execution into the invocation; reject it before it reaches the command line.
    with pytest.raises(ValueError, match="must not start with '-'"):
        scp(source="/local/file.txt", target="-oProxyCommand=touch pwned:/x")
    mock_subprocess.assert_not_called()


def test_scp_rejects_option_like_source(mock_subprocess):
    with pytest.raises(ValueError, match="must not start with '-'"):
        scp(source="-oProxyCommand=touch pwned:/x", target="/local/file.txt")
    mock_subprocess.assert_not_called()
