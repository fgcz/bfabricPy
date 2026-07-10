import contextlib
import hashlib
import os
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError
from typing import Literal

import httpx
import pytest
from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import (
    prepare_resolved_file,
    _operation_copy_rsync,
    _operation_copy_cp,
    _operation_copy_http,
    _operation_link_symbolic,
    _operation_copy_scp,
    _verify_checksum,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceLocal,
    FileSourceSsh,
    FileSourceSshValue,
)
from logot import Logot, logged

from bfabric import Bfabric


def _http_source(url: str, *, auth: Literal["bfabric"] | None) -> FileSourceHttp:
    return FileSourceHttp(http=FileSourceHttpValue(url=url, auth=auth))


def _http_file(url: str, *, auth: Literal["bfabric"] | None, checksum: str | None = None) -> ResolvedFile:
    return ResolvedFile(
        source=_http_source(url, auth=auth),
        filename="destination.txt",
        link=False,
        checksum=checksum,
    )


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
        return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_file.httpx.stream", return_value=cm)

    return _make


def test_operation_copy_http_anonymous_success(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth=None)

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
    source = _http_source("https://host/data/f.txt", auth="bfabric")

    result = _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token="jwt-token")

    assert result is True
    headers = stream.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jwt-token"


def test_operation_copy_http_require_auth_without_token_raises(tmp_path):
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth="bfabric")

    with pytest.raises(RuntimeError, match="OAuth-backed client"):
        _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token=None)


def test_operation_copy_http_does_not_send_token_when_not_required(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth=None)

    _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token="jwt-token")

    # Even if a token is available, an anonymous (auth=None) URL must not receive it.
    headers = stream.call_args.kwargs["headers"]
    assert "Authorization" not in headers


def test_operation_copy_http_http_error_returns_false(mock_http_stream, tmp_path):
    mock_http_stream(body=b"", raise_error=httpx.HTTPError("403 Forbidden"))
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth=None)

    result = _operation_copy_http(source=source, output_path=output_path, checksum=None, bearer_token=None)

    assert result is False


def test_operation_copy_http_checksum_ok(mock_http_stream, tmp_path):
    body = b"payload"
    checksum = hashlib.md5(body).hexdigest()
    mock_http_stream(body=body)
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth=None)

    assert _operation_copy_http(source=source, output_path=output_path, checksum=checksum, bearer_token=None) is True


def test_operation_copy_http_checksum_mismatch_raises(mock_http_stream, tmp_path):
    mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    source = _http_source("https://host/data/f.txt", auth=None)

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        _operation_copy_http(source=source, output_path=output_path, checksum="deadbeef", bearer_token=None)


def test_verify_checksum_ok(tmp_path):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")
    checksum = hashlib.md5(b"payload").hexdigest()

    _verify_checksum(tmp_file, checksum, tmp_path / "out.txt")  # does not raise
    assert tmp_file.exists()


def test_verify_checksum_mismatch_raises(tmp_path):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        _verify_checksum(tmp_file, "deadbeef", tmp_path / "out.txt")

    assert not tmp_file.exists()


def test_verify_checksum_none_skips_and_warns(tmp_path, logot: Logot):
    tmp_file = tmp_path / "download.part"
    tmp_file.write_bytes(b"payload")
    output_path = tmp_path / "out.txt"

    _verify_checksum(tmp_file, None, output_path)

    logot.assert_logged(logged.warning(f"No checksum available for {output_path}; skipping integrity verification."))


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

    mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_file.httpx.stream", side_effect=fake_stream)
    return seen


def test_operation_copy_http_strips_auth_on_cross_origin_redirect(mocker, tmp_path):
    # The trust boundary relies on httpx dropping Authorization when a storage URL redirects off-origin
    # (e.g. to a presigned CDN link); guard that behavior so an httpx upgrade cannot silently break it.
    seen = _patch_redirecting_stream(mocker, redirect_to="https://cdn.example/redirected")
    source = _http_source("https://storage.example/file", auth="bfabric")

    result = _operation_copy_http(
        source=source, output_path=tmp_path / "out.txt", checksum=None, bearer_token="jwt-token"
    )

    assert result is True
    assert seen["storage.example"]["Authorization"] == "Bearer jwt-token"
    assert "authorization" not in seen["cdn.example"]


def test_operation_copy_http_keeps_auth_on_same_origin_redirect(mocker, tmp_path):
    # A same-origin redirect must still carry the token, otherwise legitimate storage redirects break.
    seen = _patch_redirecting_stream(mocker, redirect_to="https://storage.example/redirected")
    source = _http_source("https://storage.example/file", auth="bfabric")

    result = _operation_copy_http(
        source=source, output_path=tmp_path / "out.txt", checksum=None, bearer_token="jwt-token"
    )

    assert result is True
    assert seen["storage.example"]["Authorization"] == "Bearer jwt-token"


def test_prepare_resolved_file_routes_http(mocker, tmp_path):
    mock_http = mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_http", return_value=True
    )
    mock_rsync = mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_rsync", return_value=True
    )
    file = _http_file("https://host/data/f.txt", auth="bfabric")

    prepare_resolved_file(file=file, working_dir=tmp_path, context=PrepareContext(bearer_token="tok"))

    mock_http.assert_called_once_with(
        source=file.source, output_path=tmp_path / "destination.txt", checksum=None, bearer_token="tok"
    )
    mock_rsync.assert_not_called()


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def mock_shutil_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.fixture
def mock_scp(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_file.scp")


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(spec=Bfabric)


@pytest.fixture
def operation_copy_rsync(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_rsync", return_value=False
    )


@pytest.fixture
def operation_copy_scp(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_scp", return_value=False
    )


@pytest.fixture
def operation_copy_cp(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_cp", return_value=False
    )


@pytest.fixture
def operation_link_symbolic(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_link_symbolic", return_value=False
    )


def test_prepare_local_copy_when_rsync_success(operation_copy_rsync) -> None:
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    operation_copy_rsync.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext())
    operation_copy_rsync.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt", None
    )


def test_prepare_local_copy_when_fallback_success(operation_copy_rsync, operation_copy_cp) -> None:
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    operation_copy_rsync.return_value = False
    operation_copy_cp.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext())
    operation_copy_rsync.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt", None
    )
    operation_copy_cp.assert_called_once_with(file.source, Path("../../integration/working_dir") / "destination.txt")


def test_prepare_local_link_when_success(operation_link_symbolic):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=True, checksum=None)
    operation_link_symbolic.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext())
    operation_link_symbolic.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt"
    )


def test_prepare_remote_copy_when_rsync_success(operation_copy_rsync):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    operation_copy_rsync.return_value = True
    prepare_resolved_file(
        file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext(ssh_user="user")
    )
    operation_copy_rsync.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt", "user"
    )


def test_prepare_remote_copy_when_fallback_success(operation_copy_rsync, operation_copy_scp):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    operation_copy_rsync.return_value = False
    operation_copy_scp.return_value = True
    prepare_resolved_file(
        file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext(ssh_user="user")
    )
    operation_copy_rsync.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt", "user"
    )
    operation_copy_scp.assert_called_once_with(
        file.source, Path("../../integration/working_dir") / "destination.txt", "user"
    )


def test_prepare_link_raises_for_non_local_source():
    # Guards the invariant FileSpec.validate_no_link_remote is supposed to establish upstream: a
    # ResolvedFile that somehow reached here with link=True and a remote source must fail loud
    # rather than being passed to _operation_link_symbolic, which assumes a local source.
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=True, checksum=None
    )
    with pytest.raises(RuntimeError, match="Cannot link a non-local file"):
        prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), context=PrepareContext())


def test_operation_copy_rsync_local(mock_subprocess, logot: Logot):
    source = FileSourceLocal(local="/source.txt")
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-rltvP", "--", "/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -rltvP -- /source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_default(mock_subprocess, logot: Logot):
    source = FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.txt"))
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(
        ["rsync", "-rltvP", "--", "host:/source.txt", "mock_output.txt"], check=False
    )
    logot.assert_logged(logged.info("rsync -rltvP -- host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_custom_user(mock_subprocess, logot: Logot):
    source = FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.txt"))
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_subprocess.assert_called_once_with(
        ["rsync", "-rltvP", "--", "user@host:/source.txt", "mock_output.txt"], check=False
    )
    logot.assert_logged(logged.info("rsync -rltvP -- user@host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_scp(mock_scp):
    source = FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.txt"))
    result = _operation_copy_scp(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert result


def test_operation_copy_scp_when_error(mock_scp):
    mock_scp.side_effect = CalledProcessError(1, "scp")
    source = FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.txt"))
    result = _operation_copy_scp(source=source, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert not result


def test_operation_copy_cp(mock_shutil_copyfile, logot: Logot):
    source = FileSourceLocal(local="/source.txt")
    result = _operation_copy_cp(source=source, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert result


def test_operation_copy_cp_when_error(mock_shutil_copyfile, logot: Logot):
    mock_shutil_copyfile.side_effect = SameFileError
    source = FileSourceLocal(local="/source.txt")
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
    source = FileSourceLocal(local=source_path)
    mock_subprocess.return_value.returncode = 0
    result = _operation_link_symbolic(source=source, output_path=Path(dest))
    mock_subprocess.assert_called_once_with(["ln", "-s", expected_target, str(dest)], check=False)
    logot.assert_logged(logged.info(f"ln -s {expected_target} {dest}"))
    assert result


def test_operation_link_symbolic_recognizes_existing_correct_link(mock_subprocess, logot: Logot, tmp_path):
    # An already-correct relative symlink must be recognized regardless of the process CWD. The check
    # used to resolve the relative target against the CWD (and take output_path.resolve().parent, which
    # follows the existing link), so a correct link was only recognized when run from its own directory
    # and was otherwise needlessly torn down and recreated.
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    source_file = src_dir / "source.txt"
    source_file.write_text("payload")
    dst_dir = tmp_path / "dst"
    dst_dir.mkdir()
    output_path = dst_dir / "destination.txt"
    # Pre-create exactly the relative link the operation itself would create.
    output_path.symlink_to(os.path.relpath(source_file, dst_dir))

    source = FileSourceLocal(local=str(source_file))
    result = _operation_link_symbolic(source=source, output_path=output_path)

    assert result is True
    logot.assert_logged(logged.info("Link already exists and points to the correct file"))
    # The link was already correct, so it must not be recreated.
    mock_subprocess.assert_not_called()
