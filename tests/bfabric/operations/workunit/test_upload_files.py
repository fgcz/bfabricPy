"""Unit tests for :func:`bfabric.operations.workunit.upload_files`.

Fully mock-based: the REST client (``UploadRestClient``), the checksum collector
(``collect_file_infos``) and the byte mover (``send_to_sink``) are patched at their
use sites in ``bfabric.operations.workunit.upload`` so no live B-Fabric or real files
are touched. The tests exercise the orchestration and the failure-cleanup path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bfabric.operations.workunit import (
    UploadFilesParams,
    UploadSummary,
    upload_files,
)
from bfabric.transfer import CreatedResource, DuplicateResult, FileInfo, TransferError, UploadTokenResult
from bfabric.transfer.errors import BfabricTransferError, ScopeError

WORKUNIT_ID = 555


@pytest.fixture
def mock_client(mocker):
    client = mocker.MagicMock(name="Bfabric")
    client.config.base_url = "https://bfabric.example/"
    # Every workunit save (create, complete, mark-failed) returns an indexable [dict]; only
    # create/complete consume result[0] (via Workunit(...).id).
    client.save.return_value = [{"id": WORKUNIT_ID}]
    return client


@pytest.fixture
def rest(mocker):
    rest_mock = mocker.MagicMock(name="UploadRestClient")
    mocker.patch("bfabric.operations.workunit.upload.UploadRestClient", return_value=rest_mock)
    return rest_mock


@pytest.fixture
def mock_collect(mocker):
    return mocker.patch("bfabric.operations.workunit.upload.collect_file_infos")


@pytest.fixture
def mock_send(mocker):
    return mocker.patch("bfabric.operations.workunit.upload.send_to_sink")


def _file_infos(*names: str) -> list[FileInfo]:
    return [FileInfo(name=n, md5=f"md5-{n}", size=1, path=Path(f"/src/{n}")) for n in names]


def _created(*names: str) -> list[CreatedResource]:
    return [
        CreatedResource(
            id=10 + i,
            name=n,
            storage_path=f"/store/{n}",
            import_resource_id=90 + i,
        )
        for i, n in enumerate(names)
    ]


def _dupes(**action_by_name: str) -> list[DuplicateResult]:
    return [DuplicateResult(filename=name, category="new", action=action) for name, action in action_by_name.items()]


def _params(**overrides) -> UploadFilesParams:
    return UploadFilesParams(container_id=100, application_id=5, **overrides)


def _create_payload(mock_client) -> dict | None:
    """The create-workunit save payload (identified by the ``containerid`` key), or None."""
    for call in mock_client.save.call_args_list:
        if call.args[0] == "workunit" and "containerid" in call.args[1]:
            return call.args[1]
    return None


def _status_updates(mock_client) -> list[str]:
    """The status strings from every ``{"id": ..., "status": ...}`` workunit save, in order."""
    return [
        call.args[1]["status"]
        for call in mock_client.save.call_args_list
        if call.args[0] == "workunit" and set(call.args[1]) == {"id", "status"}
    ]


def _job_payload(mock_client) -> dict | None:
    """The create-job save payload, or None if no job was created."""
    for call in mock_client.save.call_args_list:
        if call.args[0] == "job":
            return call.args[1]
    return None


def _distinct_job_id(mock_client, *, job_id: int) -> None:
    """Make ``job`` saves return a distinct id so it can't be confused with the workunit's."""

    def _save(endpoint, _obj, **_kwargs):
        return [{"id": job_id}] if endpoint == "job" else [{"id": WORKUNIT_ID}]

    mock_client.save.side_effect = _save


class TestHappyPath:
    def test_uploads_all_files_and_completes(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        assert summary == UploadSummary(
            workunit_id=WORKUNIT_ID,
            uploaded=2,
            skipped=0,
            failed=0,
            uploads=summary.uploads,
            failures=[],
        )
        assert summary.workunit_id == WORKUNIT_ID
        assert {u.filename for u in summary.uploads} == {"a.txt", "b.txt"}
        assert mock_send.call_count == 2
        # Workunit ends 'available' and is never flipped to 'failed'.
        assert _status_updates(mock_client) == ["available"]

    def test_records_resource_details(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params())

        upload = summary.uploads[0]
        assert upload.filename == "a.txt"
        assert upload.resource_id == 10
        assert upload.storage_path == "/store/a.txt"
        assert upload.import_resource_id == 90


class TestDuplicateCheck:
    def test_all_skipped_creates_nothing(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip", "b.txt": "skip"})

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        assert summary == UploadSummary(workunit_id=None, uploaded=0, skipped=2, failed=0)
        # No workunit created, no resources created, no transfer attempted.
        mock_client.save.assert_not_called()
        rest.create_resources.assert_not_called()
        mock_send.assert_not_called()

    def test_force_skips_check(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params(force=True))

        rest.check_duplicates.assert_not_called()
        assert summary.uploaded == 2
        assert summary.skipped == 0
        assert mock_send.call_count == 2

    def test_missing_verdict_rejected(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        # The server returns a verdict only for a.txt (b.txt omitted / name-normalized away).
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        with pytest.raises(BfabricTransferError, match="no verdict"):
            upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())
        # Rejected during dedup, before workunit creation -> no silent drop.
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_link_verdict_rejected(self, mock_client, rest, mock_collect, mock_send):
        # The server may classify a content-identical/renamed duplicate as action="link" (register a link
        # to existing content instead of uploading bytes). upload_files does not implement linking, and
        # the old code silently folded "link" into the skipped count -> the requested file was never
        # registered yet reported as a success. It must now fail loud instead.
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "link"})
        with pytest.raises(BfabricTransferError, match="link"):
            upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())
        # Rejected during dedup, before any workunit creation or transfer -> no silent drop.
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_unknown_action_rejected(self, mock_client, rest, mock_collect, mock_send):
        # Any action the client doesn't understand is treated like "link": fail loud rather than guess.
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "quarantine"})
        with pytest.raises(BfabricTransferError):
            upload_files(mock_client, [Path("/src/a.txt")], _params())
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()


class TestFailureCleanup:
    def test_partial_failure_still_completes(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        # First file succeeds, second raises a TransferError (recorded, run continues).
        mock_send.side_effect = [mocker.MagicMock(), TransferError("network hiccup")]

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        assert summary.uploaded == 1
        assert summary.failed == 1
        assert summary.failures[0].filename == "b.txt"
        assert summary.uploads[0].filename == "a.txt"
        # Some file succeeded -> workunit completed 'available', never marked 'failed'.
        assert _status_updates(mock_client) == ["available"]
        mock_client.delete.assert_not_called()

    def test_all_transfers_fail_marks_failed(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = TransferError("everything is down")

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        assert summary.uploaded == 0
        assert summary.failed == 2
        assert summary.workunit_id == WORKUNIT_ID
        # No usable content -> workunit flipped to 'failed', and never deleted.
        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()

    def test_setup_failure_marks_failed_and_reraises(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.side_effect = BfabricTransferError("create-resources 500")

        with pytest.raises(BfabricTransferError, match="create-resources 500"):
            upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        # Workunit was created then flipped to 'failed' during cleanup; never deleted.
        assert _create_payload(mock_client) is not None
        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()
        mock_send.assert_not_called()

    def test_resource_pairing_mismatch_marks_failed_and_reraises(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        # One resource returned for two files -> _pair_resources_to_files raises.
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        with pytest.raises(BfabricTransferError, match="cannot reliably pair"):
            upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params())

        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()
        mock_send.assert_not_called()

    def test_duplicate_resource_names_rejected(self, mock_client, rest, mock_collect, mock_send):
        # Two files that map to the same resource name would silently collapse under name-based pairing.
        mock_collect.return_value = _file_infos("data.txt", "data.txt")
        rest.check_duplicates.return_value = _dupes(**{"data.txt": "upload"})
        rest.create_resources.return_value = _created("data.txt", "data.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        with pytest.raises(BfabricTransferError, match="same resource name"):
            upload_files(mock_client, [Path("/src/data.txt"), Path("/src/data.txt")], _params())
        assert _status_updates(mock_client) == ["failed"]
        mock_send.assert_not_called()


class TestAuditAttributes:
    def test_written_as_custom_attributes(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        upload_files(mock_client, [Path("/src/a.txt")], _params(), audit_attributes={"origin": "test"})

        create_payload = _create_payload(mock_client)
        assert create_payload is not None
        assert {"name": "origin", "value": "test"} in create_payload["customattribute"]


class TestProgressCallbacks:
    def test_on_start_fires_once_with_count_and_total_bytes(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = [
            FileInfo(name="a.txt", md5="md5-a", size=100, path=Path("/src/a.txt")),
            FileInfo(name="b.txt", md5="md5-b", size=200, path=Path("/src/b.txt")),
        ]
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        on_start = mocker.Mock()

        upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params(), on_start=on_start)

        on_start.assert_called_once_with(2, 300)

    def test_on_start_not_fired_when_all_skipped(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip"})
        on_start = mocker.Mock()

        upload_files(mock_client, [Path("/src/a.txt")], _params(), on_start=on_start)

        on_start.assert_not_called()

    def test_on_file_done_fires_per_file_on_success(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        on_file_done = mocker.Mock()

        upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params(), on_file_done=on_file_done)

        assert on_file_done.call_args_list == [mocker.call("a.txt", True), mocker.call("b.txt", True)]

    def test_on_file_done_reports_failure(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = [mocker.MagicMock(), TransferError("network hiccup")]
        on_file_done = mocker.Mock()

        upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params(), on_file_done=on_file_done)

        assert on_file_done.call_args_list == [mocker.call("a.txt", True), mocker.call("b.txt", False)]


class TestPreflight:
    """Fail-fast checks that run before any workunit is created."""

    def test_non_oauth_client_rejected_before_any_work(self, mock_client, mock_collect, mock_send):
        # No `rest` fixture: the real UploadRestClient runs and require_oauth fires, so a classic
        # login+password client is refused before its password could be sent as a bearer token.
        mock_client.auth.login = "someuser"
        with pytest.raises(BfabricTransferError, match="OAuth-backed"):
            upload_files(mock_client, [Path("/src/a.txt")], _params())
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_missing_tus_extra_fails_fast(self, mocker, mock_client, mock_collect, mock_send):
        mocker.patch(
            "bfabric.transfer.upload.importlib.import_module",
            side_effect=ImportError("No module named 'tusclient'"),
        )
        mock_collect.return_value = _file_infos("a.txt")
        with pytest.raises(BfabricTransferError, match="transfer extra"):
            upload_files(mock_client, [Path("/src/a.txt")], _params())
        # Fails before any workunit is created or bytes moved.
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_missing_tus_scope_fails_before_workunit_creation(self, mocker, mock_client, rest, mock_collect, mock_send):
        # A token lacking the 'tus' scope must be caught up front, so a scope-less client never leaves an
        # orphaned 'failed' workunit behind (the scope check used to run only at initiate time).
        mocker.patch(
            "bfabric.operations.workunit.upload.check_upload_scope",
            side_effect=ScopeError("token does not grant the 'tus' scope"),
        )
        mock_collect.return_value = _file_infos("a.txt")
        with pytest.raises(ScopeError, match="'tus' scope"):
            upload_files(mock_client, [Path("/src/a.txt")], _params())
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        mock_send.assert_not_called()


class TestReuseExistingWorkunit:
    def test_does_not_create_workunit(self, mock_client, rest, mock_collect, mock_send):
        # The reused workunit lives in container 777; params still carry the (ignored) create-path 100.
        mock_client.read.return_value = [{"container": {"id": 777}}]
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999))

        assert summary.workunit_id == 999
        assert summary.uploaded == 1
        # No workunit was created and its status was never flipped — we don't own a reused workunit.
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        # Dedup + resources target the reused workunit's container/id, resolved via read (not params).
        rest.check_duplicates.assert_called_once_with(777, mock_collect.return_value)
        assert rest.create_resources.call_args.args[0] == 999

    def test_not_found_raises(self, mock_client, rest, mock_collect, mock_send):
        mock_client.read.return_value = []
        mock_collect.return_value = _file_infos("a.txt")

        with pytest.raises(BfabricTransferError, match="not found"):
            upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999))

        # Resolution fails before dedup / creation / any transfer.
        rest.check_duplicates.assert_not_called()
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_all_duplicates_skipped_reports_workunit_id(self, mock_client, rest, mock_collect, mock_send):
        # On the reuse path, "all skipped" means the files already live in the targeted workunit, so the
        # summary must report that workunit's id — not None, which reads as "no workunit involved" and is
        # only correct on the create path (where nothing was created).
        mock_client.read.return_value = [{"container": {"id": 777}}]
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip"})

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999))

        assert summary == UploadSummary(workunit_id=999, uploaded=0, skipped=1, failed=0)
        # Nothing created, nothing flipped, no transfer attempted.
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        mock_send.assert_not_called()

    def test_all_transfers_fail_does_not_mark_failed(self, mock_client, rest, mock_collect, mock_send):
        mock_client.read.return_value = [{"container": {"id": 777}}]
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = TransferError("down")

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999))

        assert summary.uploaded == 0
        assert summary.failed == 1
        # A reused workunit is never flipped to 'failed' — its lifecycle is not ours to change.
        assert _status_updates(mock_client) == []

    def test_setup_failure_does_not_mark_failed_and_reraises(self, mock_client, rest, mock_collect, mock_send):
        mock_client.read.return_value = [{"container": {"id": 777}}]
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.side_effect = BfabricTransferError("boom")

        with pytest.raises(BfabricTransferError, match="boom"):
            upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999))

        assert _status_updates(mock_client) == []


class TestJobTracking:
    def test_creates_job_and_threads_id(self, mock_client, rest, mock_collect, mock_send):
        _distinct_job_id(mock_client, job_id=777)
        mock_collect.return_value = _file_infos("a.txt", "b.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt"), Path("/src/b.txt")], _params(track_job=True))

        # A UPLOAD/NEW job is created, parented to the workunit.
        assert _job_payload(mock_client) == {
            "action": "UPLOAD",
            "status": "NEW",
            "parentclassname": "Workunit",
            "parentid": WORKUNIT_ID,
        }
        assert summary.job_id == 777
        # job_id is threaded into the token request and into every sink's metadata.
        assert rest.get_upload_token.call_args.kwargs["job_id"] == 777
        sink = mock_send.call_args_list[0].args[0]
        assert sink.metadata["jobId"] == "777"

    def test_off_by_default_creates_no_job(self, mock_client, rest, mock_collect, mock_send):
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params())

        assert _job_payload(mock_client) is None
        assert summary.job_id is None
        assert rest.get_upload_token.call_args.kwargs["job_id"] is None
        sink = mock_send.call_args_list[0].args[0]
        assert "jobId" not in sink.metadata

    def test_on_reuse_path_does_not_touch_workunit(self, mock_client, rest, mock_collect, mock_send):
        _distinct_job_id(mock_client, job_id=888)
        mock_client.read.return_value = [{"container": {"id": 777}}]
        mock_collect.return_value = _file_infos("a.txt")
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, [Path("/src/a.txt")], _params(workunit_id=999, track_job=True))

        # The job is parented to the reused workunit; the workunit itself is never created or flipped.
        assert _job_payload(mock_client)["parentid"] == 999
        assert summary.job_id == 888
        assert rest.get_upload_token.call_args.kwargs["job_id"] == 888
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []


class TestParamsValidation:
    def test_workunit_id_and_name_mutually_exclusive(self):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            UploadFilesParams(workunit_id=1, workunit_name="x")

    def test_requires_container_and_application_without_id(self):
        with pytest.raises(ValidationError, match="required unless workunit_id"):
            UploadFilesParams(container_id=100)  # missing application_id and no workunit_id

    def test_workunit_id_alone_is_valid(self):
        params = UploadFilesParams(workunit_id=42)
        assert params.workunit_id == 42
        assert params.container_id is None
