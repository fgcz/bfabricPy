"""Tests for the thin app-runner adapter over ``bfabric.transfer.fetch_to_path``.

The byte-moving operations themselves (rsync/scp/cp/symlink/HTTP + checksum verification) now live
in ``bfabric.transfer._generic`` and are tested there; here we only cover the spec->transport adapter,
the ``PrepareContext``->``Credentials`` mapping, and that ``prepare_resolved_file`` delegates correctly.
"""

from pathlib import Path
from typing import Literal

import pytest
from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import (
    _to_credentials,
    _to_transfer_source,
    prepare_resolved_file,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceLocal,
    FileSourceSsh,
    FileSourceSshValue,
)
from bfabric.transfer import (
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
)


def _http_source(url: str, *, auth: Literal["bfabric"] | None) -> FileSourceHttp:
    return FileSourceHttp(http=FileSourceHttpValue(url=url, auth=auth))


def _http_file(url: str, *, auth: Literal["bfabric"] | None, checksum: str | None = None) -> ResolvedFile:
    return ResolvedFile(source=_http_source(url, auth=auth), filename="destination.txt", link=False, checksum=checksum)


# --- adapter: spec FileSource* -> flat TransferSource ---


def test_to_transfer_source_local():
    assert _to_transfer_source(FileSourceLocal(local="/source.txt")) == TransferSourceLocal(path=Path("/source.txt"))


def test_to_transfer_source_ssh():
    source = FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.txt"))
    assert _to_transfer_source(source) == TransferSourceSsh(host="host", path="/source.txt")


@pytest.mark.parametrize("auth", [None, "bfabric"])
def test_to_transfer_source_http(auth):
    source = FileSourceHttp(http=FileSourceHttpValue(url="https://host/f.txt", auth=auth))
    assert _to_transfer_source(source) == TransferSourceHttp(url="https://host/f.txt", auth=auth)


# --- credentials mapping ---


def test_to_credentials_without_token():
    creds = _to_credentials(PrepareContext(ssh_user="user"))
    assert creds.ssh_user == "user"
    assert creds.token_provider is None


def test_to_credentials_with_token():
    creds = _to_credentials(PrepareContext(ssh_user="user", token_provider=lambda: "tok"))
    assert creds.ssh_user == "user"
    assert creds.token_provider is not None
    assert creds.token_provider() == "tok"


# --- prepare_resolved_file delegates to fetch_to_path ---


@pytest.fixture
def mock_fetch(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_file.fetch_to_path")


def test_prepare_resolved_file_routes_http(mock_fetch, tmp_path):
    file = _http_file("https://host/data/f.txt", auth="bfabric")
    prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext(token_provider=lambda: "tok"))

    (source, dest, creds), kwargs = mock_fetch.call_args
    assert source == TransferSourceHttp(url="https://host/data/f.txt", auth="bfabric")
    assert dest == tmp_path / "destination.txt"
    assert creds.token_provider() == "tok"
    assert kwargs == {"checksum": None, "link_ok": False}


def test_prepare_resolved_file_local(mock_fetch, tmp_path):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum="abc")
    prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext(ssh_user="user"))

    (source, dest, creds), kwargs = mock_fetch.call_args
    assert source == TransferSourceLocal(path=Path("/source.txt"))
    assert dest == tmp_path / "destination.txt"
    assert creds.ssh_user == "user"
    assert kwargs == {"checksum": "abc", "link_ok": False}


def test_prepare_resolved_file_ssh(mock_fetch, tmp_path):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext(ssh_user="user"))

    (source, _dest, creds), kwargs = mock_fetch.call_args
    assert source == TransferSourceSsh(host="host", path="/source.txt")
    assert creds.ssh_user == "user"
    assert kwargs == {"checksum": None, "link_ok": False}


def test_prepare_resolved_file_link(mock_fetch, tmp_path):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=True, checksum=None)
    prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext())

    (source, _dest, _creds), kwargs = mock_fetch.call_args
    assert source == TransferSourceLocal(path=Path("/source.txt"))
    assert kwargs == {"checksum": None, "link_ok": True}


def test_prepare_link_raises_for_non_local_source(tmp_path):
    # End-to-end (real fetch_to_path): a link=True with a remote source must fail loud rather than
    # attempting to symlink a remote path. Guards the invariant FileSpec.validate_no_link_remote sets.
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=True, checksum=None
    )
    with pytest.raises(RuntimeError, match="Cannot link a non-local file"):
        prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext())
