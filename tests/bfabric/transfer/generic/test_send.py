from __future__ import annotations

import subprocess
import sys
from subprocess import CalledProcessError

import pytest
from bfabric.transfer._generic import _tus_mover
from bfabric.transfer._generic._upload_types import UploadOutcome
from bfabric.transfer._generic.credentials import Credentials
from bfabric.transfer._generic.errors import TransferError
from bfabric.transfer._generic.send import send_to_sink
from bfabric.transfer._generic.sinks import TransferSinkLocal, TransferSinkScp, TransferSinkTus


def test_send_local_copies_file(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    dest = tmp_path / "out" / "dest.bin"

    outcome = send_to_sink(TransferSinkLocal(path=dest), src, Credentials())

    assert dest.read_bytes() == b"payload"
    assert outcome == UploadOutcome(bytes_uploaded=7, final_offset=7, upload_url=None)


def test_send_local_reports_progress(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    progress: list[tuple[int, int]] = []

    send_to_sink(
        TransferSinkLocal(path=tmp_path / "dest.bin"),
        src,
        Credentials(),
        on_progress=lambda d, t: progress.append((d, t)),
    )

    assert progress == [(7, 7)]


def test_send_scp_invokes_scp(mocker, tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    mock_scp = mocker.patch("bfabric.transfer._generic.send.scp")

    outcome = send_to_sink(TransferSinkScp(host="storage", path="/data/dest.bin"), src, Credentials(ssh_user="bfabric"))

    mock_scp.assert_called_once_with(source=src, target="storage:/data/dest.bin", user="bfabric")
    assert outcome.upload_url is None
    assert outcome.bytes_uploaded == 7


def test_send_scp_error_wrapped(mocker, tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    mocker.patch("bfabric.transfer._generic.send.scp", side_effect=CalledProcessError(1, "scp"))

    with pytest.raises(TransferError, match="scp of"):
        send_to_sink(TransferSinkScp(host="storage", path="/data/dest.bin"), src, Credentials())


def test_send_tus_delegates_to_mover(mocker, tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    sentinel = UploadOutcome(bytes_uploaded=7, final_offset=7, upload_url="https://tus/x")
    mock_upload = mocker.patch.object(_tus_mover, "upload_file", return_value=sentinel)

    sink = TransferSinkTus(endpoint="https://tus.example/", metadata={"resourceId": "1"}, token="tus-tok")
    on_progress = mocker.Mock()
    on_url = mocker.Mock()
    outcome = send_to_sink(
        sink, src, Credentials(), on_progress=on_progress, resume_url="https://tus.example/r", on_url=on_url
    )

    mock_upload.assert_called_once_with(
        "https://tus.example/",
        "tus-tok",
        src,
        {"resourceId": "1"},
        on_progress=on_progress,
        resume_url="https://tus.example/r",
        on_url=on_url,
    )
    assert outcome is sentinel


@pytest.mark.slow
def test_importing_transfer_does_not_import_tuspy():
    # The core lazy-import guarantee: a download-only / query consumer that merely imports the
    # transfer facade (and its send module) must never pull tusclient/tuspy. Checked in a fresh
    # interpreter so an earlier test that imported the tus mover cannot mask a regression.
    code = (
        "import sys; import bfabric.transfer; import bfabric.transfer._generic.send; "
        "assert 'tusclient' not in sys.modules, sorted(m for m in sys.modules if 'tus' in m)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
