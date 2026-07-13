from pathlib import Path

import pytest
from bfabric_app_runner.output_registration.register import copy_file_to_storage
from bfabric_app_runner.specs.outputs_spec import CopyResourceSpec
from bfabric.transfer import Credentials, TransferSinkScp


def _workunit_definition(mocker, output_folder: Path):
    wd = mocker.MagicMock()
    wd.registration.storage_output_folder = output_folder
    return wd


def test_copy_file_to_storage_scp_routes_through_transfer_package(mocker):
    mock_send = mocker.patch("bfabric_app_runner.output_registration.register.send_to_sink")
    storage = mocker.MagicMock()
    storage.scp_prefix = "storagehost:/base/path/"
    wd = _workunit_definition(mocker, Path("out/folder"))
    spec = CopyResourceSpec(local_path=Path("/local/result.txt"), store_entry_path=Path("result.txt"))

    copy_file_to_storage(spec, workunit_definition=wd, storage=storage, ssh_user="bfabric")

    mock_send.assert_called_once_with(
        TransferSinkScp(host="storagehost", path="/base/path/out/folder/result.txt"),
        Path("/local/result.txt"),
        Credentials(ssh_user="bfabric"),
    )


def test_copy_file_to_storage_scp_rejects_storage_without_scp_prefix(mocker):
    # A storage not configured for scp exposes scp_prefix=None; fail with a clear message
    # rather than crashing on the string split.
    storage = mocker.MagicMock()
    storage.scp_prefix = None
    wd = _workunit_definition(mocker, Path("out"))
    spec = CopyResourceSpec(local_path=Path("/l/r.txt"), store_entry_path=Path("r.txt"))

    with pytest.raises(ValueError, match="not configured for scp"):
        copy_file_to_storage(spec, workunit_definition=wd, storage=storage, ssh_user=None)


def test_copy_file_to_storage_tus_not_yet_wired(mocker):
    # protocol="tus" is a valid spec value now, but the app-runner output path is not wired for it.
    storage = mocker.MagicMock()
    storage.scp_prefix = "h:/b/"
    wd = _workunit_definition(mocker, Path("out"))
    spec = CopyResourceSpec(local_path=Path("/l/r.txt"), store_entry_path=Path("r.txt"), protocol="tus")

    with pytest.raises(NotImplementedError, match="tus output transport is not yet wired"):
        copy_file_to_storage(spec, workunit_definition=wd, storage=storage, ssh_user=None)
