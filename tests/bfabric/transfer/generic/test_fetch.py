from __future__ import annotations

import contextlib
import hashlib
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError

import httpx
import pytest
from logot import Logot, logged

from bfabric.transfer._generic.credentials import Credentials
from bfabric.transfer._generic.errors import TransferError
from bfabric.transfer._generic.fetch import (
    _operation_copy_cp,
    _operation_copy_http,
    _operation_copy_rsync,
    _operation_copy_scp,
    _operation_link_symbolic,
    _verify_checksum,
    fetch_to_path,
)
from bfabric.transfer._generic.sources import (
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
)

# --- HTTP operation -------------------------------------------------------------------------------


@pytest.fixture
def mock_http_stream(mocker):
    """Patches httpx.stream to yield a response with the given body; returns (patch, set_body)."""

    def _make(body: bytes = b"hello world", raise_error: BaseException | None = None):
        response = mocker.MagicMock()
        response.iter_bytes.return_value = [body]
        response.raise_for_status.side_effect = raise_error
        cm = mocker.MagicMock()
        cm.__enter__.return_value = response
        cm.__exit__.return_value = False
        return mocker.patch("bfabric.transfer._generic.fetch.httpx.stream", return_value=cm)

    return _make


def test_operation_copy_http_anonymous_success(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth=None)

    result = _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token=None)

    assert result is True
    assert output_path.read_bytes() == b"payload"
    # No Authorization header for anonymous downloads.
    headers = stream.call_args.kwargs["headers"]
    assert "Authorization" not in headers
    assert stream.call_args.kwargs["follow_redirects"] is True


def test_operation_copy_http_sends_bearer_when_required(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth="bfabric")

    result = _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token="jwt-token")

    assert result is True
    headers = stream.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jwt-token"


def test_operation_copy_http_require_auth_without_token_raises(tmp_path):
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth="bfabric")

    with pytest.raises(TransferError, match="OAuth-backed client"):
        _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token=None)


def test_operation_copy_http_does_not_send_token_when_not_required(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth=None)

    _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token="jwt-token")

    # Even if a token is available, an anonymous (auth=None) URL must not receive it.
    headers = stream.call_args.kwargs["headers"]
    assert "Authorization" not in headers


def test_operation_copy_http_http_error_returns_false(mock_http_stream, tmp_path):
    mock_http_stream(body=b"", raise_error=httpx.HTTPError("403 Forbidden"))
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth=None)

    result = _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token=None)

    assert result is False


def test_operation_copy_http_checksum_ok(mock_http_stream, tmp_path):
    body = b"payload"
    checksum = hashlib.md5(body).hexdigest()
    mock_http_stream(body=body)
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth=None)

    assert _operation_copy_http(source=source, output_path=output_path, checksum=checksum, bearer_token=None) is True


def test_operation_copy_http_checksum_mismatch_raises(mock_http_stream, tmp_path):
    mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = TransferSourceHttp(url="https://host/data/f.txt", auth=None)

    with pytest.raises(TransferError, match="Checksum mismatch"):
        _operation_copy_http(source=source, output_path=output_path, checksum="deadbeef", bearer_token=None)


# --- checksum verification ------------------------------------------------------------------------


def test_verify_checksum_ok(tmp_path):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")
    checksum = hashlib.md5(b"payload").hexdigest()

    _verify_checksum(tmp_file, checksum, tmp_path / "out.txt")  # does not raise
    assert tmp_file.exists()


def test_verify_checksum_mismatch_raises(tmp_path):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")

    with pytest.raises(TransferError, match="Checksum mismatch"):
        _verify_checksum(tmp_file, "deadbeef", tmp_path / "out.txt")

    assert not tmp_file.exists()


def test_verify_checksum_none_skips_and_warns(tmp_path, logot: Logot):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")
    output_path = tmp_path / "out.txt"

    _verify_checksum(tmp_file, None, output_path)

    logot.assert_logged(logged.warning(f"No checksum available for {output_path}; skipping integrity verification."))


# --- redirect / trust-boundary behavior -----------------------------------------------------------


def _patch_redirecting_stream(mocker, redirect_to: str) -> dict[str, httpx.Headers]:
    """Patches httpx.stream so a GET to ``/file`` 302-redirects to ``redirect_to``.

    Routes the download through a real httpx client backed by MockTransport, so httpx's own
    cross-origin ``Authorization``-stripping is actually exercised. Returns a per-host record of the
    request headers seen by the transport.
    """
    seen: dict[str, httpx.Headers] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.host] = request.headers
        if request.url.path == "/file":
            return httpx.Response(302, headers={"Location": redirect_to})
        return httpx.Response(200, content=b"payload")

    transport = httpx.MockTransport(handler)

    @contextlib.contextmanager
    def fake_stream(method, url, *, headers=None, follow_redirects=False, **kwargs):
        with httpx.Client(transport=transport, follow_redirects=follow_redirects) as client:
            with client.stream(method, url, headers=headers) as response:
                yield response

    mocker.patch("bfabric.transfer._generic.fetch.httpx.stream", side_effect=fake_stream)
    return seen


def test_operation_copy_http_strips_auth_on_cross_origin_redirect(mocker, tmp_path):
    # The trust boundary relies on httpx dropping Authorization when a storage URL redirects off-origin
    # (e.g. to a presigned CDN link); guard that behavior so an httpx upgrade cannot silently break it.
    seen = _patch_redirecting_stream(mocker, redirect_to="https://cdn.example/redirected")
    source = TransferSourceHttp(url="https://storage.example/file", auth="bfabric")

    result = _operation_copy_http(
        source=source, output_path=tmp_path / "out.txt", checksum=None, bearer_token="jwt-token"
    )

    assert result is True
    assert seen["storage.example"]["Authorization"] == "Bearer jwt-token"
    assert "authorization" not in seen["cdn.example"]


def test_operation_copy_http_keeps_auth_on_same_origin_redirect(mocker, tmp_path):
    # A same-origin redirect must still carry the token, otherwise legitimate storage redirects break.
    seen = _patch_redirecting_stream(mocker, redirect_to="https://storage.example/redirected")
    source = TransferSourceHttp(url="https://storage.example/file", auth="bfabric")

    result = _operation_copy_http(
        source=source, output_path=tmp_path / "out.txt", checksum=None, bearer_token="jwt-token"
    )

    assert result is True
    assert seen["storage.example"]["Authorization"] == "Bearer jwt-token"


# --- rsync / scp / cp / symlink operations --------------------------------------------------------


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def mock_shutil_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.fixture
def mock_scp(mocker):
    return mocker.patch("bfabric.transfer._generic.fetch.scp")


def test_operation_copy_rsync_local(mock_subprocess, logot: Logot):
    source = TransferSourceLocal(path=Path("/source.txt"))
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-rltvP", "/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -rltvP /source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_default(mock_subprocess, logot: Logot):
    source = TransferSourceSsh(host="host", path="/source.txt")
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-rltvP", "host:/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -rltvP host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_custom_user(mock_subprocess, logot: Logot):
    source = TransferSourceSsh(host="host", path="/source.txt")
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_subprocess.assert_called_once_with(
        ["rsync", "-rltvP", "user@host:/source.txt", "mock_output.txt"], check=False
    )
    logot.assert_logged(logged.info("rsync -rltvP user@host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_scp(mock_scp):
    source = TransferSourceSsh(host="host", path="/source.txt")
    result = _operation_copy_scp(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert result


def test_operation_copy_scp_when_error(mock_scp):
    mock_scp.side_effect = CalledProcessError(1, "scp")
    source = TransferSourceSsh(host="host", path="/source.txt")
    result = _operation_copy_scp(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert not result


def test_operation_copy_cp(mock_shutil_copyfile, logot: Logot):
    source = TransferSourceLocal(path=Path("/source.txt"))
    result = _operation_copy_cp(source=source, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert result


def test_operation_copy_cp_when_error(mock_shutil_copyfile, logot: Logot):
    mock_shutil_copyfile.side_effect = SameFileError
    source = TransferSourceLocal(path=Path("/source.txt"))
    result = _operation_copy_cp(source=source, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert not result


@pytest.mark.parametrize(
    "source_path,dest,expected_target",
    [
        ("/E/source.txt", "/E/dir/destination.txt", "../source.txt"),
        ("/X/source.txt", "/E/dir/destination.txt", "../../X/source.txt"),
        ("/work/source.txt", "/work/destination.txt", "source.txt"),
    ],
)
def test_operation_link_symbolic(mock_subprocess, logot: Logot, source_path, dest, expected_target):
    source = TransferSourceLocal(path=Path(source_path))
    mock_subprocess.return_value.returncode = 0
    result = _operation_link_symbolic(source=source, output_path=Path(dest))
    mock_subprocess.assert_called_once_with(["ln", "-s", expected_target, str(dest)], check=False)
    logot.assert_logged(logged.info(f"ln -s {expected_target} {dest}"))
    assert result


# --- fetch_to_path dispatch (new; the old dispatch tests stay in app-runner) ----------------------


@pytest.fixture
def op_rsync(mocker):
    return mocker.patch("bfabric.transfer._generic.fetch._operation_copy_rsync", return_value=False)


@pytest.fixture
def op_cp(mocker):
    return mocker.patch("bfabric.transfer._generic.fetch._operation_copy_cp", return_value=False)


@pytest.fixture
def op_scp(mocker):
    return mocker.patch("bfabric.transfer._generic.fetch._operation_copy_scp", return_value=False)


@pytest.fixture
def op_link(mocker):
    return mocker.patch("bfabric.transfer._generic.fetch._operation_link_symbolic", return_value=False)


def test_fetch_to_path_routes_http(mocker, tmp_path, op_rsync):
    mock_http = mocker.patch("bfabric.transfer._generic.fetch._operation_copy_http", return_value=True)
    source = TransferSourceHttp(url="https://host/data/f.txt", auth="bfabric")
    dest = tmp_path / "destination.txt"

    fetch_to_path(source, dest, Credentials(token_provider=lambda: "tok"))

    mock_http.assert_called_once_with(source=source, output_path=dest, checksum=None, bearer_token="tok")
    op_rsync.assert_not_called()


def test_fetch_to_path_local_falls_back_to_cp(op_rsync, op_cp, tmp_path):
    op_rsync.return_value = False
    op_cp.return_value = True
    source = TransferSourceLocal(path=Path("/source.txt"))
    dest = tmp_path / "destination.txt"

    fetch_to_path(source, dest, Credentials())

    op_rsync.assert_called_once_with(source, dest, None)
    op_cp.assert_called_once_with(source, dest)


def test_fetch_to_path_ssh_falls_back_to_scp(op_rsync, op_scp, tmp_path):
    op_rsync.return_value = False
    op_scp.return_value = True
    source = TransferSourceSsh(host="host", path="/source.txt")
    dest = tmp_path / "destination.txt"

    fetch_to_path(source, dest, Credentials(ssh_user="user"))

    op_rsync.assert_called_once_with(source, dest, "user")
    op_scp.assert_called_once_with(source, dest, "user")


def test_fetch_to_path_local_link(op_link, tmp_path):
    op_link.return_value = True
    source = TransferSourceLocal(path=Path("/source.txt"))
    dest = tmp_path / "destination.txt"

    fetch_to_path(source, dest, Credentials(), link_ok=True)

    op_link.assert_called_once_with(source, dest)


def test_fetch_to_path_link_raises_for_non_local_source(tmp_path):
    source = TransferSourceSsh(host="host", path="/source.txt")
    dest = tmp_path / "destination.txt"

    with pytest.raises(TransferError, match="Cannot link a non-local file"):
        fetch_to_path(source, dest, Credentials(), link_ok=True)


def test_fetch_to_path_raises_when_all_operations_fail(op_rsync, op_cp, tmp_path):
    op_rsync.return_value = False
    op_cp.return_value = False
    source = TransferSourceLocal(path=Path("/source.txt"))
    dest = tmp_path / "destination.txt"

    with pytest.raises(TransferError, match="Failed to fetch"):
        fetch_to_path(source, dest, Credentials())
