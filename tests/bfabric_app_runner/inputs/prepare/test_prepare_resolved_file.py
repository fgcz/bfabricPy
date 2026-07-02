import hashlib
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError

import httpx
import pytest
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import (
    prepare_resolved_file,
    _operation_copy_rsync,
    _operation_copy_cp,
    _operation_copy_http,
    _operation_link_symbolic,
    _operation_copy_scp,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import FileSourceHttp, FileSourceHttpValue
from logot import Logot, logged

from bfabric import Bfabric


def _http_file(url: str, *, require_auth: bool, checksum: str | None = None) -> ResolvedFile:
    return ResolvedFile(
        source=FileSourceHttp(http=FileSourceHttpValue(url=url, require_auth=require_auth)),
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
    file = _http_file("https://host/data/f.txt", require_auth=False)

    result = _operation_copy_http(file=file, output_path=output_path, bearer_token=None)

    assert result is True
    assert output_path.read_bytes() == b"payload"
    # No Authorization header for anonymous downloads.
    headers = stream.call_args.kwargs["headers"]
    assert "Authorization" not in headers
    assert stream.call_args.kwargs["follow_redirects"] is True


def test_operation_copy_http_sends_bearer_when_required(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=True)

    result = _operation_copy_http(file=file, output_path=output_path, bearer_token="jwt-token")

    assert result is True
    headers = stream.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jwt-token"


def test_operation_copy_http_require_auth_without_token_raises(tmp_path):
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=True)

    with pytest.raises(RuntimeError, match="OAuth-backed client"):
        _operation_copy_http(file=file, output_path=output_path, bearer_token=None)


def test_operation_copy_http_does_not_send_token_when_not_required(mock_http_stream, tmp_path):
    stream = mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=False)

    _operation_copy_http(file=file, output_path=output_path, bearer_token="jwt-token")

    # Even if a token is available, an anonymous (require_auth=False) URL must not receive it.
    headers = stream.call_args.kwargs["headers"]
    assert "Authorization" not in headers


def test_operation_copy_http_http_error_returns_false(mock_http_stream, tmp_path):
    mock_http_stream(body=b"", raise_error=httpx.HTTPError("403 Forbidden"))
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=False)

    result = _operation_copy_http(file=file, output_path=output_path, bearer_token=None)

    assert result is False


def test_operation_copy_http_checksum_ok(mock_http_stream, tmp_path):
    body = b"payload"
    checksum = hashlib.md5(body).hexdigest()
    mock_http_stream(body=body)
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=False, checksum=checksum)

    assert _operation_copy_http(file=file, output_path=output_path, bearer_token=None) is True


def test_operation_copy_http_checksum_mismatch_raises(mock_http_stream, tmp_path):
    mock_http_stream(body=b"payload")
    output_path = tmp_path / "out.txt"
    file = _http_file("https://host/data/f.txt", require_auth=False, checksum="deadbeef")

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        _operation_copy_http(file=file, output_path=output_path, bearer_token=None)


def test_prepare_resolved_file_routes_http(mocker, tmp_path):
    mock_http = mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_http", return_value=True
    )
    mock_rsync = mocker.patch(
        "bfabric_app_runner.inputs.prepare.prepare_resolved_file._operation_copy_rsync", return_value=True
    )
    file = _http_file("https://host/data/f.txt", require_auth=True)

    prepare_resolved_file(file=file, working_dir=tmp_path, ssh_user=None, bearer_token="tok")

    mock_http.assert_called_once_with(file, tmp_path / "destination.txt", "tok")
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
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), ssh_user=None)
    operation_copy_rsync.assert_called_once_with(file, Path("../../integration/working_dir") / "destination.txt", None)


def test_prepare_local_copy_when_fallback_success(operation_copy_rsync, operation_copy_cp) -> None:
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    operation_copy_rsync.return_value = False
    operation_copy_cp.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), ssh_user=None)
    operation_copy_rsync.assert_called_once_with(file, Path("../../integration/working_dir") / "destination.txt", None)
    operation_copy_cp.assert_called_once_with(file, Path("../../integration/working_dir") / "destination.txt")


def test_prepare_local_link_when_success(operation_link_symbolic):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=True, checksum=None)
    operation_link_symbolic.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), ssh_user=None)
    operation_link_symbolic.assert_called_once_with(file, Path("../../integration/working_dir") / "destination.txt")


def test_prepare_remote_copy_when_rsync_success(operation_copy_rsync):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    operation_copy_rsync.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), ssh_user="user")
    operation_copy_rsync.assert_called_once_with(
        file, Path("../../integration/working_dir") / "destination.txt", "user"
    )


def test_prepare_remote_copy_when_fallback_success(operation_copy_rsync, operation_copy_scp):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    operation_copy_rsync.return_value = False
    operation_copy_scp.return_value = True
    prepare_resolved_file(file=file, working_dir=Path("../../integration/working_dir"), ssh_user="user")
    operation_copy_rsync.assert_called_once_with(
        file, Path("../../integration/working_dir") / "destination.txt", "user"
    )
    operation_copy_scp.assert_called_once_with(file, Path("../../integration/working_dir") / "destination.txt", "user")


def test_operation_copy_rsync_local(mock_subprocess, logot: Logot):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(file=file, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-rltvP", "/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -rltvP /source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_default(mock_subprocess, logot: Logot):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(file=file, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-rltvP", "host:/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -rltvP host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_custom_user(mock_subprocess, logot: Logot):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(file=file, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_subprocess.assert_called_once_with(
        ["rsync", "-rltvP", "user@host:/source.txt", "mock_output.txt"], check=False
    )
    logot.assert_logged(logged.info("rsync -rltvP user@host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_scp(mock_scp):
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    result = _operation_copy_scp(file=file, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert result


def test_operation_copy_scp_when_error(mock_scp):
    mock_scp.side_effect = CalledProcessError(1, "scp")
    file = ResolvedFile(
        source={"ssh": {"host": "host", "path": "/source.txt"}}, filename="destination.txt", link=False, checksum=None
    )
    result = _operation_copy_scp(file=file, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert not result


def test_operation_copy_cp(mock_shutil_copyfile, logot: Logot):
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    result = _operation_copy_cp(file=file, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert result


def test_operation_copy_cp_when_error(mock_shutil_copyfile, logot: Logot):
    mock_shutil_copyfile.side_effect = SameFileError
    file = ResolvedFile(source={"local": "/source.txt"}, filename="destination.txt", link=False, checksum=None)
    result = _operation_copy_cp(file=file, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert not result


@pytest.mark.parametrize(
    "source,dest,expected_target",
    [
        ("/E/source.txt", "/E/dir/destination.txt", "../source.txt"),
        ("/X/source.txt", "/E/dir/destination.txt", "../../X/source.txt"),
        ("/work/source.txt", "/work/destination.txt", "source.txt"),
    ],
)
def test_operation_link_symbolic(mock_subprocess, logot: Logot, source, dest, expected_target):
    file = ResolvedFile(source={"local": source}, filename="destination.txt", link=True, checksum=None)
    mock_subprocess.return_value.returncode = 0
    result = _operation_link_symbolic(file=file, output_path=Path(dest))
    mock_subprocess.assert_called_once_with(["ln", "-s", expected_target, str(dest)], check=False)
    logot.assert_logged(logged.info(f"ln -s {expected_target} {dest}"))
    assert result
