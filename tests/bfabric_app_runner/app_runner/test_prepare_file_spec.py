from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError

import pytest
from logot import Logot, logged

from bfabric_app_runner.inputs.list_inputs import (
    prepare_file_spec,
    _operation_copy_rsync,
    _operation_copy_cp,
    _operation_link_symbolic,
    _operation_copy_scp,
)
from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric import Bfabric


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def mock_shutil_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(spec=Bfabric)


@pytest.fixture
def operation_copy_rsync(mocker):
    return mocker.patch(
        "bfabric_app_runner.input_preparation.prepare_file_spec._operation_copy_rsync", return_value=False
    )


@pytest.fixture
def operation_copy_scp(mocker):
    return mocker.patch(
        "bfabric_app_runner.input_preparation.prepare_file_spec._operation_copy_scp", return_value=False
    )


@pytest.fixture
def operation_copy_cp(mocker):
    return mocker.patch("bfabric_app_runner.input_preparation.prepare_file_spec._operation_copy_cp", return_value=False)


@pytest.fixture
def operation_link_symbolic(mocker):
    return mocker.patch(
        "bfabric_app_runner.input_preparation.prepare_file_spec._operation_link_symbolic", return_value=False
    )


# TODO should absolute path  for filename be mandatory in the future? -> this could also have unwanted side effects


def test_prepare_local_copy_when_rsync_success(mock_client, operation_copy_rsync) -> None:
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt"})
    operation_copy_rsync.return_value = True
    prepare_file_spec(spec=spec, client=mock_client, working_dir=Path("../integration/working_dir"), ssh_user=None)
    operation_copy_rsync.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt", None)


def test_prepare_local_copy_when_fallback_success(mock_client, operation_copy_rsync, operation_copy_cp) -> None:
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt"})
    operation_copy_rsync.return_value = False
    operation_copy_cp.return_value = True
    prepare_file_spec(spec=spec, client=mock_client, working_dir=Path("../integration/working_dir"), ssh_user=None)
    operation_copy_rsync.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt", None)
    operation_copy_cp.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt")


def test_prepare_local_link_when_success(mock_client, operation_link_symbolic):
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt", "link": True})
    operation_link_symbolic.return_value = True
    prepare_file_spec(spec=spec, client=mock_client, working_dir=Path("../integration/working_dir"), ssh_user=None)
    operation_link_symbolic.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt")


def test_prepare_remote_copy_when_rsync_success(mock_client, operation_copy_rsync):
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    operation_copy_rsync.return_value = True
    prepare_file_spec(spec=spec, client=mock_client, working_dir=Path("../integration/working_dir"), ssh_user="user")
    operation_copy_rsync.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt", "user")


def test_prepare_remote_copy_when_fallback_success(mock_client, operation_copy_rsync, operation_copy_scp):
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    operation_copy_rsync.return_value = False
    operation_copy_scp.return_value = True
    prepare_file_spec(spec=spec, client=mock_client, working_dir=Path("../integration/working_dir"), ssh_user="user")
    operation_copy_rsync.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt", "user")
    operation_copy_scp.assert_called_once_with(spec, Path("../integration/working_dir") / "destination.txt", "user")


def test_operation_copy_rsync_local(mock_subprocess, logot: Logot):
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt"})
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(spec=spec, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-Pav", "/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -Pav /source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_default(mock_subprocess, logot: Logot):
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(spec=spec, output_path=Path("mock_output.txt"), ssh_user=None)
    mock_subprocess.assert_called_once_with(["rsync", "-Pav", "host:/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -Pav host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_rsync_ssh_custom_user(mock_subprocess, logot: Logot):
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    mock_subprocess.return_value.returncode = 0
    result = _operation_copy_rsync(spec=spec, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_subprocess.assert_called_once_with(["rsync", "-Pav", "user@host:/source.txt", "mock_output.txt"], check=False)
    logot.assert_logged(logged.info("rsync -Pav user@host:/source.txt mock_output.txt"))
    assert result


def test_operation_copy_scp(mocker):
    mock_scp = mocker.patch("bfabric_app_runner.input_preparation.prepare_file_spec.scp")
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    result = _operation_copy_scp(spec=spec, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert result


def test_operation_copy_scp_when_error(mocker):
    mock_scp = mocker.patch(
        "bfabric_app_runner.input_preparation.prepare_file_spec.scp", side_effect=CalledProcessError(1, "scp")
    )
    spec = FileSpec.model_validate(
        {"source": {"ssh": {"host": "host", "path": "/source.txt"}}, "filename": "destination.txt"}
    )
    result = _operation_copy_scp(spec=spec, output_path=Path("mock_output.txt"), ssh_user="user")
    mock_scp.assert_called_once_with(source="host:/source.txt", target=Path("mock_output.txt"), user="user")
    assert not result


def test_operation_copy_cp(mock_shutil_copyfile, logot: Logot):
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt"})
    result = _operation_copy_cp(spec=spec, output_path=Path("mock_output.txt"))
    mock_shutil_copyfile.assert_called_once_with("/source.txt", "mock_output.txt")
    logot.assert_logged(logged.info("cp /source.txt mock_output.txt"))
    assert result


def test_operation_copy_cp_when_error(mock_shutil_copyfile, logot: Logot):
    mock_shutil_copyfile.side_effect = SameFileError
    spec = FileSpec.model_validate({"source": {"local": "/source.txt"}, "filename": "destination.txt"})
    result = _operation_copy_cp(spec=spec, output_path=Path("mock_output.txt"))
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
    spec = FileSpec.model_validate({"source": {"local": source}, "filename": "IGNORED", "link": True})
    mock_subprocess.return_value.returncode = 0
    result = _operation_link_symbolic(spec=spec, output_path=Path(dest))
    mock_subprocess.assert_called_once_with(["ln", "-s", expected_target, str(dest)], check=False)
    logot.assert_logged(logged.info(f"ln -s {expected_target} {dest}"))
    assert result
