from __future__ import annotations

from pathlib import Path

import pytest

from bfabric.transfer._generic.scp import _is_remote, scp


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


def test_is_remote():
    assert _is_remote("host:/path") is True
    assert _is_remote("user@host:/path") is True
    assert _is_remote("host:relative/path") is True
    assert _is_remote("/local/path") is False
    assert _is_remote(Path("/local/path")) is False
    # A Windows drive letter is a local path, not a host:path spec.
    assert _is_remote("C:\\Users\\file.txt") is False
    assert _is_remote("C:/Users/file.txt") is False
    # A colon after the first path separator belongs to the local path, not a host.
    assert _is_remote("./weird:name") is False


def test_scp_rejects_both_remote(mock_subprocess):
    with pytest.raises(ValueError, match="not both"):
        scp(source="host1:/a", target="host2:/b")
    mock_subprocess.assert_not_called()


def test_scp_rejects_neither_remote(mock_subprocess):
    with pytest.raises(ValueError, match="not both"):
        scp(source="/a", target="/b")
    mock_subprocess.assert_not_called()


def test_scp_rejects_directory_target(mock_subprocess):
    with pytest.raises(ValueError, match="not a directory"):
        scp(source="host:/remote/file.txt", target="/local/dir/")
    mock_subprocess.assert_not_called()


def test_scp_upload_prepends_user_and_makes_remote_dir(mocker, mock_subprocess):
    # remote target (upload): user@ is prepended to the target, and the remote parent is created via ssh.
    scp(source="/local/file.txt", target="host:/remote/dir/file.txt", user="alice")

    assert mock_subprocess.call_args_list == [
        mocker.call(["ssh", "alice@host", "mkdir", "-p", Path("/remote/dir")], check=True),
        mocker.call(["scp", "/local/file.txt", "alice@host:/remote/dir/file.txt"], check=True),
    ]


def test_scp_download_prepends_user_and_makes_local_dir(mock_subprocess, tmp_path):
    # remote source (download): user@ is prepended to the source, and the local parent is created directly.
    target = tmp_path / "sub" / "file.txt"
    scp(source="host:/remote/file.txt", target=target, user="bob")

    assert (tmp_path / "sub").is_dir()
    mock_subprocess.assert_called_once_with(["scp", "bob@host:/remote/file.txt", str(target)], check=True)


def test_scp_no_mkdir_skips_directory_creation(mock_subprocess, tmp_path):
    target = tmp_path / "sub" / "file.txt"
    scp(source="host:/remote/file.txt", target=target, mkdir=False)

    assert not (tmp_path / "sub").exists()
    mock_subprocess.assert_called_once_with(["scp", "host:/remote/file.txt", str(target)], check=True)
