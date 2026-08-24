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
    FileSkip,
    UploadFileParam,
    UploadFilesParams,
    UploadSummary,
    WorkunitCompletionError,
    upload_files,
)
from bfabric.operations.workunit.upload import _describe_dropped
from bfabric.transfer import CreatedResource, DuplicateResult, FileInfo, TransferError, UploadTokenResult
from bfabric.transfer.errors import BfabricTransferError, ScopeError
from bfabric.transfer.resume_cache import ResumeCache

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


@pytest.fixture(autouse=True)
def mock_collect(mocker):
    """The collector, faked as one :class:`FileInfo` per input path, named after its basename.

    Autouse, so no test can reach the real filesystem; request it by name only to reconfigure it.

    ``upload_files`` calls it once per :class:`UploadFileParam` (that is how a file keeps the
    ``on_duplicate`` of the entry it came from), so a plain ``return_value`` would hand the same
    infos back for every entry. A test that needs an entry to expand into several files -- a
    directory -- or needs specific sizes sets ``side_effect`` to a list holding one result per entry.
    """
    mock = mocker.patch("bfabric.operations.workunit.upload.collect_file_infos")
    mock.side_effect = lambda paths, **_kwargs: _file_infos(*(p.name for p in paths))
    return mock


@pytest.fixture(autouse=True)
def isolate_resume_cache(mocker, tmp_path):
    """Keep the default resume cache out of the real ``~/.bfabric``.

    Autouse because resuming is on by default: any test that transfers a file would otherwise write
    to the developer's home directory and leak state between runs.
    """
    return mocker.patch(
        "bfabric.operations.workunit.upload.compute_resume_cache_path",
        return_value=tmp_path / "default-resume.json",
    )


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


def _dupes(*, category: str = "new", **action_by_name: str) -> list[DuplicateResult]:
    return [DuplicateResult(filename=name, category=category, action=action) for name, action in action_by_name.items()]


def _params(*files: str | UploadFileParam, on_duplicate: str = "upload", **overrides) -> UploadFilesParams:
    """Params for ``files``, given as paths sharing ``on_duplicate`` or as explicit entries (mixed policies)."""
    entries = [
        f if isinstance(f, UploadFileParam) else UploadFileParam(path=Path(f), on_duplicate=on_duplicate) for f in files
    ]
    return UploadFilesParams(**{"container_id": 100, "application_id": 5, "files": entries, **overrides})


def _counts(summary: UploadSummary) -> tuple[int, int, int, int]:
    """(uploaded, linked, skipped, failed) as the lengths of the four outcome lists."""
    return len(summary.uploads), len(summary.links), len(summary.skips), len(summary.failures)


def _checked_names(rest) -> list[str]:
    """The resource names actually submitted to ``check-duplicates``."""
    return [fi.name for fi in rest.check_duplicates.call_args.args[1]]


def _created_names(rest) -> list[str]:
    """The resource names submitted to ``create-resources``, in order."""
    return [fi.name for fi in rest.create_resources.call_args.args[1]]


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
    def test_uploads_all_files_and_completes(self, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        assert summary == UploadSummary(workunit_id=WORKUNIT_ID, uploads=summary.uploads)
        assert summary.workunit_id == WORKUNIT_ID
        assert {u.filename for u in summary.uploads} == {"a.txt", "b.txt"}
        assert mock_send.call_count == 2
        # Workunit ends 'available' and is never flipped to 'failed'.
        assert _status_updates(mock_client) == ["available"]

    def test_default_policy_skips_the_duplicate_check(self, mock_client, rest, mock_send):
        # on_duplicate defaults to "upload": the files are sent unconditionally, so there is no
        # verdict to ask for and check-duplicates is never called.
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        rest.check_duplicates.assert_not_called()
        assert (len(summary.uploads), len(summary.skips)) == (2, 0)
        assert mock_send.call_count == 2

    def test_records_resource_details(self, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt"))

        upload = summary.uploads[0]
        assert upload.filename == "a.txt"
        assert upload.resource_id == 10
        assert upload.storage_path == "/store/a.txt"
        assert upload.import_resource_id == 90


class TestExcludeNames:
    def test_forwarded_to_collector(self, mock_client, rest, mock_collect, mock_send):
        rest.create_resources.return_value = _created("src")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        _ = upload_files(mock_client, _params("/src"), exclude_names={".marker"})

        assert mock_collect.call_args.kwargs["exclude_names"] == {".marker"}

    def test_omitted_passes_none(self, mock_client, rest, mock_collect, mock_send):
        rest.create_resources.return_value = _created("src")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        _ = upload_files(mock_client, _params("/src"))

        assert mock_collect.call_args.kwargs["exclude_names"] is None


class TestPerFilePolicy:
    """``on_duplicate`` is carried per entry, so one call can mix policies."""

    def test_only_non_upload_entries_are_checked(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = _dupes(**{"b.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(
            mock_client,
            _params(
                UploadFileParam(path=Path("/src/a.txt"), on_duplicate="upload"),
                UploadFileParam(path=Path("/src/b.txt"), on_duplicate="skip"),
            ),
        )

        # Only the "skip" entry needs a verdict; the "upload" entry bypasses the check...
        assert _checked_names(rest) == ["b.txt"]
        # ...and still keeps its position in the list handed to create-resources.
        assert _created_names(rest) == ["a.txt", "b.txt"]
        assert (len(summary.uploads), len(summary.skips)) == (2, 0)

    def test_unchecked_entry_survives_a_duplicate_sibling(self, mock_client, rest, mock_send):
        # The "skip" entry is a duplicate and drops out; the "upload" entry is unaffected by it.
        rest.check_duplicates.return_value = _dupes(**{"b.txt": "skip"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(
            mock_client,
            _params(
                UploadFileParam(path=Path("/src/a.txt"), on_duplicate="upload"),
                UploadFileParam(path=Path("/src/b.txt"), on_duplicate="skip"),
            ),
        )

        assert _created_names(rest) == ["a.txt"]
        assert (len(summary.uploads), len(summary.skips)) == (1, 1)

    def test_directory_entry_applies_its_policy_to_every_expanded_file(self, mock_client, rest, mock_collect):
        # One entry expanding to two files: both inherit the entry's "skip", so both are checked.
        mock_collect.side_effect = [_file_infos("run/a.raw", "run/b.raw")]
        rest.check_duplicates.return_value = _dupes(**{"run/a.raw": "skip", "run/b.raw": "skip"})

        summary = upload_files(mock_client, _params("/src/run", on_duplicate="skip"))

        assert _checked_names(rest) == ["run/a.raw", "run/b.raw"]
        assert len(summary.skips) == 2

    def test_verdict_for_an_unchecked_file_is_ignored(self, mock_client, rest, mock_send):
        # A server that volunteers a verdict for a file we never submitted (here the "upload" entry)
        # must not derail the run: there is no policy to judge that verdict against.
        rest.check_duplicates.return_value = _dupes(**{"b.txt": "upload", "a.txt": "skip"})
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(
            mock_client,
            _params(
                UploadFileParam(path=Path("/src/a.txt"), on_duplicate="upload"),
                UploadFileParam(path=Path("/src/b.txt"), on_duplicate="skip"),
            ),
        )

        assert _checked_names(rest) == ["b.txt"]
        assert (len(summary.uploads), len(summary.skips)) == (2, 0)

    def test_duplicate_names_across_entries_rejected_before_creation(self, mock_client, rest, mock_send):
        # Two entries mapping to one resource name are ambiguous -- verdicts are keyed by name only,
        # so neither the policy nor the resource could be attributed. Refuse before anything is created.
        with pytest.raises(BfabricTransferError, match="same resource name"):
            upload_files(mock_client, _params("/src/data.txt", "/other/data.txt"))

        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        rest.create_resources.assert_not_called()
        mock_send.assert_not_called()


class TestDuplicateCheck:
    def test_all_skipped_creates_nothing(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip", "b.txt": "skip"})

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="skip"))

        assert summary == UploadSummary(
            workunit_id=None,
            skips=[FileSkip(filename="a.txt", category="new"), FileSkip(filename="b.txt", category="new")],
        )
        # No workunit created, no resources created, no transfer attempted.
        mock_client.save.assert_not_called()
        rest.create_resources.assert_not_called()
        mock_send.assert_not_called()

    def test_skip_records_the_duplicate_it_lost_out_to(self, mock_client, rest, mock_send):
        # The count alone couldn't say which files were dropped, nor which stored bytes they matched.
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt", category="exact_duplicate", action="skip", resource_id=4711, linkable=True
            ),
            DuplicateResult(filename="b.txt", category="new", action="upload"),
        ]
        rest.create_resources.return_value = _created("b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="skip"))

        assert summary.skips == [FileSkip(filename="a.txt", category="exact_duplicate", existing_resource_id=4711)]

    def test_skip_without_an_existing_resource_leaves_the_id_unset(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="batch_duplicate", action="skip", resource_id=None)
        ]

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"))

        assert summary.skips == [FileSkip(filename="a.txt", category="batch_duplicate", existing_resource_id=None)]

    def test_missing_verdict_rejected(self, mock_client, rest, mock_send):
        # The server returns a verdict only for a.txt (b.txt omitted / name-normalized away).
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        with pytest.raises(BfabricTransferError, match="no verdict"):
            upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="skip"))
        # Rejected during dedup, before workunit creation -> no silent drop.
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_link_verdict_rejected_under_skip_policy(self, mock_client, rest, mock_send):
        # The server may classify a content-identical/renamed duplicate as action="link" (register a link
        # to existing content instead of uploading bytes). A "skip" policy does not authorize that, and
        # folding it into the skipped count would report a file as handled that was never registered.
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload", "b.txt": "link"})
        with pytest.raises(BfabricTransferError, match="link"):
            upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="skip"))
        # Rejected during dedup, before any workunit creation or transfer -> no silent drop.
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_unknown_action_rejected(self, mock_client, rest, mock_send):
        # Any action the client doesn't understand is treated like "link": fail loud rather than guess.
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "quarantine"})
        with pytest.raises(BfabricTransferError):
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"))
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()


class TestNestedNames:
    """Nested (sub-directory) resource names, which the server now echoes back verbatim."""

    def test_uploads_nested_names_without_tripping_guards(self, mock_client, rest, mock_collect, mock_send):
        # Previously the server normalized "sub/nested.raw" to its basename, so the verdict- and
        # resource-pairing guards fired and the upload was refused. With names echoed verbatim, both
        # guards see matching names and the upload proceeds.
        names = ("sub/nested.raw", "other/nested.raw")
        mock_collect.side_effect = [_file_infos(*names)]
        rest.check_duplicates.return_value = _dupes(**{n: "upload" for n in names})
        rest.create_resources.return_value = _created(*names)
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src", on_duplicate="skip"))

        # Two files sharing a basename in different subdirectories stay distinct.
        assert len(summary.uploads) == 2
        assert {u.filename for u in summary.uploads} == set(names)
        assert {u.storage_path for u in summary.uploads} == {f"/store/{n}" for n in names}
        assert mock_send.call_count == 2

    def test_renamed_duplicate_is_skipped_not_rejected(self, mock_client, rest, mock_collect, mock_send):
        # A nested re-upload now reports category "renamed_duplicate" (name-matching misses on a
        # subpath, so detection falls back to MD5) rather than "exact_duplicate". Both carry
        # action "skip", and the client branches on action -> it must still count as skipped.
        mock_collect.side_effect = [_file_infos("sub/nested.raw")]
        rest.check_duplicates.return_value = _dupes(category="renamed_duplicate", **{"sub/nested.raw": "skip"})

        summary = upload_files(mock_client, _params("/src", on_duplicate="skip"))

        assert len(summary.skips) == 1
        assert len(summary.uploads) == 0
        mock_send.assert_not_called()


class TestLinkPolicy:
    """``on_duplicate="link"`` links a duplicate to existing content instead of skipping/failing.

    The server reports a content-duplicate as ``exact_duplicate``/``renamed_duplicate`` carrying
    ``action: "skip"`` plus an ``existingResourceId`` -- *not* ``action: "link"``. Linking is therefore
    driven by a skip verdict that names a resource to link to.
    """

    def test_skip_verdict_with_existing_resource_is_linked(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="new", action="upload"),
            DuplicateResult(
                filename="b.txt", category="exact_duplicate", action="skip", resource_id=4711, linkable=True
            ),
        ]
        created = _created("a.txt", "b.txt")
        created[1].linked = True
        rest.create_resources.return_value = created
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="link"))

        sent = rest.create_resources.call_args.args[1]
        assert [(fi.name, fi.link_from_resource_id) for fi in sent] == [("a.txt", None), ("b.txt", 4711)]
        assert mock_send.call_count == 1
        assert [u.filename for u in summary.uploads] == ["a.txt"]
        assert [u.filename for u in summary.links] == ["b.txt"]
        assert _counts(summary) == (1, 1, 0, 0)

    def test_renamed_duplicate_is_linked(self, mock_client, rest, mock_collect, mock_send):
        # The nested-folder case: MD5-matched under a different name, so category is renamed_duplicate.
        mock_collect.side_effect = [_file_infos("sub/nested.raw")]
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="sub/nested.raw", category="renamed_duplicate", action="skip", resource_id=4711, linkable=True
            )
        ]
        created = _created("sub/nested.raw")
        created[0].linked = True
        rest.create_resources.return_value = created

        summary = upload_files(mock_client, _params("/src", on_duplicate="link"))

        assert [fi.link_from_resource_id for fi in rest.create_resources.call_args.args[1]] == [4711]
        assert [u.filename for u in summary.links] == ["sub/nested.raw"]
        assert _counts(summary)[:3] == (0, 1, 0)

    def test_skip_without_existing_resource_is_still_skipped(self, mock_client, rest, mock_send):
        # Nothing to link to -> the plain skip behaviour stands, and no resource is created.
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="exact_duplicate", action="skip", resource_id=None)
        ]

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        rest.create_resources.assert_not_called()
        mock_send.assert_not_called()
        assert _counts(summary)[:3] == (0, 0, 1)

    def test_skip_policy_does_not_link(self, mock_client, rest, mock_send):
        # Per-file opt-in: under "skip" a duplicate is dropped outright, even when a link target is offered.
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt", category="exact_duplicate", action="skip", resource_id=4711, linkable=True
            )
        ]

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"))

        rest.create_resources.assert_not_called()
        assert _counts(summary)[:3] == (0, 0, 1)

    def test_link_verdict_registers_link_and_skips_transfer(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="new", action="upload"),
            DuplicateResult(
                filename="b.txt", category="renamed_duplicate", action="link", resource_id=4711, linkable=True
            ),
        ]
        created = _created("a.txt", "b.txt")
        created[1].linked = True
        rest.create_resources.return_value = created
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="link"))

        # The link verdict's existingResourceId is passed back as linkFromResourceId.
        sent = rest.create_resources.call_args.args[1]
        assert [(fi.name, fi.link_from_resource_id) for fi in sent] == [("a.txt", None), ("b.txt", 4711)]
        # Only the uploaded file's bytes move; the linked one is reported separately from uploads.
        assert mock_send.call_count == 1
        assert [u.filename for u in summary.uploads] == ["a.txt"]
        assert [u.filename for u in summary.links] == ["b.txt"]
        assert _counts(summary) == (1, 1, 0, 0)

    def test_link_verdict_rejected_under_skip_policy(self, mock_client, rest, mock_send):
        # Per-file opt-in: under "skip" the hard error stands.
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "link"})

        with pytest.raises(BfabricTransferError, match="link"):
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"))

        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_all_linked_completes_workunit_without_token(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt", category="exact_duplicate", action="link", resource_id=4711, linkable=True
            )
        ]
        created = _created("a.txt")
        created[0].linked = True
        rest.create_resources.return_value = created

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        # Nothing to transfer, but the resource exists -> complete, never mark failed.
        rest.get_upload_token.assert_not_called()
        mock_send.assert_not_called()
        assert _status_updates(mock_client) == ["available"]
        assert _counts(summary)[:2] == (0, 1)
        assert [u.filename for u in summary.links] == ["a.txt"]

    def test_link_without_existing_resource_id_rejected(self, mock_client, rest, mock_send):
        # A "link" verdict with no existingResourceId is unusable: linking is the only handling we
        # have for it, and we cannot link to nothing. Fail loud rather than silently drop the file.
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="renamed_duplicate", action="link", resource_id=None)
        ]

        with pytest.raises(BfabricTransferError, match="existingResourceId"):
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_unknown_action_still_rejected(self, mock_client, rest, mock_send):
        # "link" only teaches the client about link verdicts -- other unknown actions still fail.
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "quarantine"})

        with pytest.raises(BfabricTransferError):
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

    def test_unknown_action_hint_does_not_suggest_linking(self, mock_client, rest, mock_send):
        # A non-link verdict must not be described as a content-duplicate: suggesting the link policy
        # here would send the user down a path that cannot resolve it.
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "quarantine"})

        with pytest.raises(BfabricTransferError, match='on_duplicate="upload"') as excinfo:
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"))

        assert 'on_duplicate="link"' not in str(excinfo.value)

    def test_upload_policy_bypasses_linking(self, mock_client, rest, mock_send):
        # "upload" skips the duplicate check, so there are no verdicts and nothing can be linked.
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="upload"))

        rest.check_duplicates.assert_not_called()
        assert [fi.link_from_resource_id for fi in rest.create_resources.call_args.args[1]] == [None]
        assert _counts(summary)[:2] == (1, 0)


class TestLinkedResources:
    """``create-resources`` may return already-AVAILABLE linked resources, which carry no bytes."""

    def test_linked_resource_is_not_transferred_or_initiated(self, mock_client, rest, mock_send):
        created = _created("a.txt", "b.txt")
        created[1].linked = True
        rest.create_resources.return_value = created
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        # The linked resource has no bytes to send: excluded from initiate's ids and never transferred.
        assert rest.get_upload_token.call_args.args[1] == [created[0].id]
        assert rest.get_upload_token.call_args.args[2] == [created[0].import_resource_id]
        assert mock_send.call_count == 1
        assert [u.filename for u in summary.uploads] == ["a.txt"]
        assert [u.filename for u in summary.links] == ["b.txt"]
        assert _counts(summary) == (1, 1, 0, 0)

    def test_all_linked_skips_transfer_entirely(self, mock_client, rest, mock_send):
        # Nothing to transfer, but the resources were registered -> the workunit must still complete
        # rather than be marked failed by the "no uploads" branch.
        created = _created("a.txt")
        created[0].linked = True
        rest.create_resources.return_value = created

        summary = upload_files(mock_client, _params("/src/a.txt"))

        mock_send.assert_not_called()
        rest.get_upload_token.assert_not_called()
        assert _counts(summary)[:3] == (0, 1, 0)
        assert [u.filename for u in summary.links] == ["a.txt"]
        assert _status_updates(mock_client) == ["available"]


class TestFailureCleanup:
    def test_partial_failure_still_completes(self, mocker, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        # First file succeeds, second raises a TransferError (recorded, run continues).
        mock_send.side_effect = [mocker.MagicMock(), TransferError("network hiccup")]

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        assert len(summary.uploads) == 1
        assert len(summary.failures) == 1
        assert summary.failures[0].filename == "b.txt"
        assert summary.uploads[0].filename == "a.txt"
        # Some file succeeded -> workunit completed 'available', never marked 'failed'.
        assert _status_updates(mock_client) == ["available"]
        mock_client.delete.assert_not_called()

    def test_all_transfers_fail_marks_failed(self, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = TransferError("everything is down")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        assert len(summary.uploads) == 0
        assert len(summary.failures) == 2
        assert summary.workunit_id == WORKUNIT_ID
        # No usable content -> workunit flipped to 'failed', and never deleted.
        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()

    def test_setup_failure_marks_failed_and_reraises(self, mock_client, rest, mock_send):
        rest.create_resources.side_effect = BfabricTransferError("create-resources 500")

        with pytest.raises(BfabricTransferError, match="create-resources 500"):
            upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        # Workunit was created then flipped to 'failed' during cleanup; never deleted.
        assert _create_payload(mock_client) is not None
        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()
        mock_send.assert_not_called()

    def test_resource_pairing_mismatch_marks_failed_and_reraises(self, mock_client, rest, mock_send):
        # One resource returned for two files -> _pair_resources_to_files raises.
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        with pytest.raises(BfabricTransferError, match="cannot reliably pair"):
            upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"))

        assert _status_updates(mock_client) == ["failed"]
        mock_client.delete.assert_not_called()
        mock_send.assert_not_called()


class TestAuditAttributes:
    def test_written_as_custom_attributes(self, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        upload_files(mock_client, _params("/src/a.txt"), audit_attributes={"origin": "test"})

        create_payload = _create_payload(mock_client)
        assert create_payload is not None
        assert {"name": "origin", "value": "test"} in create_payload["customattribute"]


class TestProgressCallbacks:
    def test_on_start_fires_once_with_count_and_total_bytes(self, mocker, mock_client, rest, mock_collect, mock_send):
        mock_collect.side_effect = [
            [FileInfo(name="a.txt", md5="md5-a", size=100, path=Path("/src/a.txt"))],
            [FileInfo(name="b.txt", md5="md5-b", size=200, path=Path("/src/b.txt"))],
        ]
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        on_start = mocker.Mock()

        upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"), on_start=on_start)

        on_start.assert_called_once_with(2, 300)

    def test_on_start_not_fired_when_all_skipped(self, mocker, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip"})
        on_start = mocker.Mock()

        upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip"), on_start=on_start)

        on_start.assert_not_called()

    def test_on_file_done_fires_per_file_on_success(self, mocker, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        on_file_done = mocker.Mock()

        upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"), on_file_done=on_file_done)

        assert on_file_done.call_args_list == [mocker.call("a.txt", True), mocker.call("b.txt", True)]

    def test_on_file_done_reports_failure(self, mocker, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = [mocker.MagicMock(), TransferError("network hiccup")]
        on_file_done = mocker.Mock()

        upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"), on_file_done=on_file_done)

        assert on_file_done.call_args_list == [mocker.call("a.txt", True), mocker.call("b.txt", False)]


class TestUrlCallback:
    def test_on_url_receives_filename_and_url_per_file(self, mocker, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        # send_to_sink fires its own on_url as soon as the server URL exists; fake that by invoking
        # the callback the mover was handed, with a per-file URL.
        mock_send.side_effect = lambda sink, path, creds, **kw: kw["on_url"](f"https://tus/{path.name}")
        on_url = mocker.Mock()

        upload_files(mock_client, _params("/src/a.txt", "/src/b.txt"), on_url=on_url)

        assert on_url.call_args_list == [
            mocker.call("a.txt", "https://tus/a.txt"),
            mocker.call("b.txt", "https://tus/b.txt"),
        ]

    def test_on_url_fires_for_a_file_whose_transfer_then_fails(self, mocker, mock_client, rest, mock_send):
        """The URL is what makes a failed transfer resumable, so it must survive the failure."""
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        def _url_then_fail(sink, path, creds, **kw):
            kw["on_url"]("https://tus/a.txt")
            raise TransferError("died mid-chunk")

        mock_send.side_effect = _url_then_fail
        on_url = mocker.Mock()

        summary = upload_files(mock_client, _params("/src/a.txt"), on_url=on_url)

        on_url.assert_called_once_with("a.txt", "https://tus/a.txt")
        assert _counts(summary) == (0, 0, 0, 1)

    def test_no_on_url_and_no_cache_passes_none_to_the_mover(self, mock_client, rest, mock_send):
        """Omitting the callback must not hand the mover a do-nothing wrapper to call per file.

        Only with resuming off: the default cache needs the callback to capture the resume URL.
        """
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        upload_files(mock_client, _params("/src/a.txt"), resume_cache=None)

        assert mock_send.call_args.kwargs["on_url"] is None


class TestPreflight:
    """Fail-fast checks that run before any workunit is created."""

    def test_non_oauth_client_rejected_before_any_work(self, mock_client, mock_collect, mock_send):
        # No `rest` fixture: the real UploadRestClient runs and require_oauth fires, so a classic
        # login+password client is refused before its password could be sent as a bearer token.
        mock_client.auth.login = "someuser"
        with pytest.raises(BfabricTransferError, match="OAuth-backed"):
            upload_files(mock_client, _params("/src/a.txt"))
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_missing_tus_extra_fails_fast(self, mocker, mock_client, mock_collect, mock_send):
        mocker.patch(
            "bfabric.transfer.upload.importlib.import_module",
            side_effect=ImportError("No module named 'tusclient'"),
        )
        with pytest.raises(BfabricTransferError, match="transfer extra"):
            upload_files(mock_client, _params("/src/a.txt"))
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
        with pytest.raises(ScopeError, match="'tus' scope"):
            upload_files(mock_client, _params("/src/a.txt"))
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        mock_send.assert_not_called()


class TestServerReportedLinkable:
    """``check-duplicates`` reports ``linkable`` per file, and it is the only authority.

    The server already knows the matched resource's status, so no extra resource read is made. A
    response that does not report it is an error rather than a guess: linking to a resource with no
    bytes behind it would register a resource pointing at nothing.
    """

    @staticmethod
    def _no_resource_reads(mock_client) -> None:
        """Fail any ``read("resource", ...)``, so a re-introduced status read is caught."""

        def _read(endpoint, obj, **_kwargs):
            if endpoint == "resource":
                raise AssertionError("resource statuses were read despite the server reporting linkable")
            return [{"id": 777, "container": {"id": 100}}]

        mock_client.read.side_effect = _read

    def test_linkable_true_is_linked_without_reading_statuses(self, mock_client, rest, mock_send):
        self._no_resource_reads(mock_client)
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt",
                category="exact_duplicate",
                action="skip",
                resource_id=4711,
                resource_status="available",
                linkable=True,
            ),
        ]
        created = _created("a.txt")
        created[0].linked = True
        rest.create_resources.return_value = created
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        sent = rest.create_resources.call_args.args[1]
        assert [(fi.name, fi.link_from_resource_id) for fi in sent] == [("a.txt", 4711)]
        assert _counts(summary) == (0, 1, 0, 0)
        assert mock_send.call_count == 0

    def test_linkable_false_is_uploaded_instead(self, mock_client, rest, mock_send):
        """The orphan case: a pending duplicate has no bytes, so send them rather than link."""
        self._no_resource_reads(mock_client)
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt",
                category="exact_duplicate",
                action="skip",
                resource_id=3166570,
                resource_status="pending",
                linkable=False,
            ),
        ]
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        sent = rest.create_resources.call_args.args[1]
        assert [(fi.name, fi.link_from_resource_id) for fi in sent] == [("a.txt", None)]
        assert _counts(summary) == (1, 0, 0, 0)
        assert mock_send.call_count == 1

    def test_mixed_verdicts_link_only_the_linkable_one(self, mock_client, rest, mock_send):
        self._no_resource_reads(mock_client)
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt",
                category="exact_duplicate",
                action="skip",
                resource_id=4711,
                resource_status="available",
                linkable=True,
            ),
            DuplicateResult(
                filename="b.txt",
                category="exact_duplicate",
                action="skip",
                resource_id=3166570,
                resource_status="failed",
                linkable=False,
            ),
        ]
        created = _created("a.txt", "b.txt")
        created[0].linked = True
        rest.create_resources.return_value = created
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        _ = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="link"))

        sent = rest.create_resources.call_args.args[1]
        assert sorted((fi.name, fi.link_from_resource_id) for fi in sent) == [("a.txt", 4711), ("b.txt", None)]

    def test_missing_linkable_is_an_error_not_a_guess(self, mock_client, rest, mock_send):
        """No `linkable` in the response: refuse rather than assume either way."""
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="exact_duplicate", action="skip", resource_id=4711),
        ]

        with pytest.raises(BfabricTransferError, match="did not report 'linkable'"):
            _ = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"))

        rest.create_resources.assert_not_called()

    def test_missing_linkable_names_every_unreported_file(self, mock_client, rest, mock_send):
        rest.check_duplicates.return_value = [
            DuplicateResult(filename="a.txt", category="exact_duplicate", action="skip", resource_id=4711),
            DuplicateResult(filename="b.txt", category="exact_duplicate", action="skip", resource_id=4712),
        ]

        with pytest.raises(BfabricTransferError) as excinfo:
            _ = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", on_duplicate="link"))

        assert "a.txt" in str(excinfo.value)
        assert "b.txt" in str(excinfo.value)


class TestDroppedTargetDescription:
    """The log line naming unlinkable targets stays bounded; a bundle can hold thousands of files."""

    def test_lists_every_target_when_there_are_few(self):
        described = _describe_dropped(["a.txt", "b.txt"], {"a.txt": 1, "b.txt": 2}, {1: "pending", 2: "failed"})

        assert described == "a.txt -> resource 1 pending, b.txt -> resource 2 failed"

    def test_truncates_and_counts_the_remainder(self):
        names = [f"f{i}.txt" for i in range(50)]
        link_ids = {name: i for i, name in enumerate(names)}

        described = _describe_dropped(names, link_ids, dict.fromkeys(range(50), "pending"))

        assert described.count(" -> resource ") == 5
        assert described.endswith("(and 45 more)")

    def test_a_target_with_no_reported_status_is_named_as_such(self):
        assert _describe_dropped(["a.txt"], {"a.txt": 7}, {}) == "a.txt -> resource 7 not found"


class TestWorkunitCompletion:
    """A failed final status flip must not lose the record of a successful upload."""

    def _fail_completion(self, mocker):
        return mocker.patch(
            "bfabric.operations.workunit.upload.complete_workunit",
            side_effect=RuntimeError("Invalid or expired token."),
        )

    def test_raises_workunit_completion_error_carrying_the_summary(self, mocker, mock_client, rest, mock_send):
        self._fail_completion(mocker)
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        with pytest.raises(WorkunitCompletionError) as excinfo:
            _ = upload_files(mock_client, _params("/src/a.txt"))

        # The bytes landed, so the caller must still be able to see what transferred.
        assert _counts(excinfo.value.summary) == (1, 0, 0, 0)
        assert [u.filename for u in excinfo.value.summary.uploads] == ["a.txt"]

    def test_original_error_is_chained(self, mocker, mock_client, rest, mock_send):
        self._fail_completion(mocker)
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        with pytest.raises(WorkunitCompletionError) as excinfo:
            _ = upload_files(mock_client, _params("/src/a.txt"))

        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_workunit_is_not_marked_failed(self, mocker, mock_client, rest, mock_send):
        """Its content is real, so it stays 'processing' rather than being flipped to failed."""
        self._fail_completion(mocker)
        marked = mocker.patch("bfabric.operations.workunit.upload.mark_workunit_failed")
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        with pytest.raises(WorkunitCompletionError):
            _ = upload_files(mock_client, _params("/src/a.txt"))

        marked.assert_not_called()

    def test_reuse_path_does_not_complete_and_so_cannot_raise(self, mocker, mock_client, rest, mock_send):
        """We don't own a caller-supplied workunit, so its status is never flipped -- nothing to fail."""
        complete = mocker.patch(
            "bfabric.operations.workunit.upload.complete_workunit", side_effect=RuntimeError("would raise")
        )
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", workunit_id=999))

        complete.assert_not_called()
        assert summary.workunit_id == 999
        assert _counts(summary) == (1, 0, 0, 0)


class TestResumeCache:
    """With a cache path, an interrupted transfer resumes instead of restarting from byte 0."""

    @staticmethod
    def _setup(rest):
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

    def test_omitted_never_resumes_and_writes_nothing(self, tmp_path, mock_client, rest, mock_send):
        self._setup(rest)
        cache = tmp_path / "resume.json"

        _ = upload_files(mock_client, _params("/src/a.txt"))

        assert not cache.exists()
        assert mock_send.call_args.kwargs.get("resume_url") is None

    def test_url_is_saved_for_a_transfer_that_then_fails(self, tmp_path, mock_client, rest, mock_send):
        """Saving on `on_url` rather than after the transfer is the point: this is the case
        the URL is worth keeping for."""
        self._setup(rest)
        cache = tmp_path / "resume.json"

        def _report_then_fail(*a, **kw):
            kw["on_url"]("https://tus/abc")
            raise TransferError("connection reset")

        mock_send.side_effect = _report_then_fail

        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert "https://tus/abc" in cache.read_text()

    def test_saved_url_is_passed_as_resume_url_on_the_next_run(self, tmp_path, mock_client, rest, mock_send):
        self._setup(rest)
        cache = tmp_path / "resume.json"

        # First run reports a URL, then fails, so the entry survives.
        def _report_then_fail(*a, **kw):
            kw["on_url"]("https://tus/abc")
            raise TransferError("connection reset")

        mock_send.side_effect = _report_then_fail
        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        mock_send.side_effect = None
        self._setup(rest)
        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert mock_send.call_args.kwargs.get("resume_url") == "https://tus/abc"

    def test_entry_is_discarded_once_the_file_transfers(self, tmp_path, mock_client, rest, mock_send):
        self._setup(rest)
        cache = tmp_path / "resume.json"
        mock_send.side_effect = lambda *a, **kw: kw["on_url"]("https://tus/abc") or None

        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        # The bytes are stored; a kept URL would only resume a completed upload.
        assert "https://tus/abc" not in cache.read_text()

    def test_stale_url_falls_back_to_a_fresh_upload(self, tmp_path, mock_client, rest, mock_send):
        """A URL the server has forgotten fails the mover's HEAD; that costs a restart, not a failure."""
        self._setup(rest)
        cache = tmp_path / "resume.json"
        ResumeCache(cache).store(
            md5="md5-a.txt", url="https://tus/gone", workunit_id=WORKUNIT_ID, resource_id=10, container_id=100
        )
        attempts: list[str | None] = []

        def _fail_only_when_resuming(*_args, **kwargs):
            attempts.append(kwargs.get("resume_url"))
            if kwargs.get("resume_url") is not None:
                raise TransferError("failed to query resume offset")

        mock_send.side_effect = _fail_only_when_resuming

        summary = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert attempts == ["https://tus/gone", None]
        assert _counts(summary) == (1, 0, 0, 0)

    def test_a_genuine_failure_without_a_resume_url_is_not_retried(self, tmp_path, mock_client, rest, mock_send):
        # Nothing to fall back to, so the error is recorded rather than costing a second attempt.
        self._setup(rest)
        mock_send.side_effect = TransferError("network is down")

        summary = upload_files(mock_client, _params("/src/a.txt"), resume_cache=tmp_path / "resume.json")

        assert mock_send.call_count == 1
        assert _counts(summary) == (0, 0, 0, 1)

    def test_cross_origin_saved_url_is_ignored(self, tmp_path, mock_client, rest, mock_send):
        # The endpoint moved; the mover refuses to send its token to the old host, so don't resume.
        self._setup(rest)
        cache = tmp_path / "resume.json"
        ResumeCache(cache).store(
            md5="md5-a.txt", url="https://old-host/abc", workunit_id=WORKUNIT_ID, resource_id=10, container_id=100
        )

        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert mock_send.call_args.kwargs.get("resume_url") is None

    def test_linked_files_are_not_cached(self, tmp_path, mock_client, rest, mock_send):
        # Nothing is sent for a linked file, so there is no upload URL to keep.
        cache = tmp_path / "resume.json"
        rest.check_duplicates.return_value = [
            DuplicateResult(
                filename="a.txt",
                category="exact_duplicate",
                action="skip",
                resource_id=4711,
                resource_status="available",
                linkable=True,
            ),
        ]
        created = _created("a.txt")
        created[0].linked = True
        rest.create_resources.return_value = created

        _ = upload_files(mock_client, _params("/src/a.txt", on_duplicate="link"), resume_cache=cache)

        mock_send.assert_not_called()
        assert not cache.exists()


class TestResumeAdoptsTheInterruptedWorkunit:
    """An interrupted upload resumes into its original workunit and resource, not a second pair.

    The motivating case is an unattended instrument upload: a multi-hundred-GB file is interrupted,
    the driving script re-runs with the same path, and it must continue against the same resource.
    A tus URL's metadata (resourceId / workunitId / storagePath) is frozen at creation, so bytes
    pushed to a saved URL land on the ORIGINAL resource no matter what the resuming run created --
    which makes creating a second workunit both wasteful and a misreport.
    """

    @staticmethod
    def _setup(rest):
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

    def _interrupt(self, mock_client, rest, mock_send, cache):
        """Run once, reporting a tus URL and then failing, so a resume entry survives."""
        self._setup(rest)

        def _report_then_fail(*_args, **kwargs):
            kwargs["on_url"]("https://tus/abc")
            raise TransferError("power cut")

        mock_send.side_effect = _report_then_fail
        return upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

    def test_second_run_creates_no_second_workunit(self, tmp_path, mock_client, rest, mock_send):
        cache = tmp_path / "resume.json"
        first = self._interrupt(mock_client, rest, mock_send, cache)
        mock_client.save.reset_mock()
        rest.create_resources.reset_mock()
        mock_send.side_effect = None

        second = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert _create_payload(mock_client) is None
        assert second.workunit_id == first.workunit_id

    def test_second_run_reuses_the_original_resource(self, tmp_path, mock_client, rest, mock_send):
        # create-resources only ever creates, so an adopted file must skip it entirely and carry the
        # remembered resource id straight into initiate -- otherwise the summary names a resource the
        # bytes never reached.
        cache = tmp_path / "resume.json"
        first = self._interrupt(mock_client, rest, mock_send, cache)
        original_resource_id = first.failures[0].resource_id
        rest.create_resources.reset_mock()
        mock_send.side_effect = None

        second = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        rest.create_resources.assert_not_called()
        assert [u.resource_id for u in second.uploads] == [original_resource_id]
        assert rest.get_upload_token.call_args.args[1] == [original_resource_id]

    def test_second_run_resumes_from_the_saved_url(self, tmp_path, mock_client, rest, mock_send):
        cache = tmp_path / "resume.json"
        _ = self._interrupt(mock_client, rest, mock_send, cache)
        mock_send.side_effect = None

        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=cache)

        assert mock_send.call_args.kwargs.get("resume_url") == "https://tus/abc"

    def test_interrupted_workunit_is_not_marked_failed(self, tmp_path, mock_client, rest, mock_send):
        # An interrupted upload is unfinished, not failed: flipping it would leave the resumable
        # workunit in a dead state that the next run then adopts.
        cache = tmp_path / "resume.json"

        _ = self._interrupt(mock_client, rest, mock_send, cache)

        assert "failed" not in _status_updates(mock_client)

    def test_resuming_is_on_by_default(self, tmp_path, mocker, mock_client, rest, mock_send):
        # Resumability that must be asked for is resumability an unattended feeder does not get, so
        # the cache defaults to a per-server path under ~/.bfabric rather than to off.
        default = tmp_path / "default-resume.json"
        mocker.patch("bfabric.operations.workunit.upload.compute_resume_cache_path", return_value=default)
        self._setup(rest)

        def _report_then_fail(*_args, **kwargs):
            kwargs["on_url"]("https://tus/abc")
            raise TransferError("power cut")

        mock_send.side_effect = _report_then_fail
        _ = upload_files(mock_client, _params("/src/a.txt"))
        mock_send.side_effect = None
        rest.create_resources.reset_mock()

        second = upload_files(mock_client, _params("/src/a.txt"))

        assert default.exists()
        rest.create_resources.assert_not_called()
        assert second.workunit_id == WORKUNIT_ID

    def test_resuming_can_be_turned_off(self, tmp_path, mocker, mock_client, rest, mock_send):
        default = tmp_path / "default-resume.json"
        mocker.patch("bfabric.operations.workunit.upload.compute_resume_cache_path", return_value=default)
        self._setup(rest)

        _ = upload_files(mock_client, _params("/src/a.txt"), resume_cache=None)

        # No cache, so the mover is given no url callback to report through and nothing is written.
        assert mock_send.call_args.kwargs.get("on_url") is None
        assert not default.exists()

    def test_the_tracking_job_is_reused_on_adoption(self, tmp_path, mock_client, rest, mock_send):
        # The tus hooks key status off jobId, and the saved URL's metadata still names the first
        # run's job. Creating a second one would leave that job hanging with nothing to finish it.
        cache = tmp_path / "resume.json"
        _distinct_job_id(mock_client, job_id=4242)
        params = _params("/src/a.txt", track_job=True)
        self._setup(rest)

        def _report_then_fail(*_args, **kwargs):
            kwargs["on_url"]("https://tus/abc")
            raise TransferError("power cut")

        mock_send.side_effect = _report_then_fail
        first = upload_files(mock_client, params, resume_cache=cache)
        mock_send.side_effect = None

        second = upload_files(mock_client, params, resume_cache=cache)

        job_saves = [c for c in mock_client.save.call_args_list if c.args[0] == "job"]
        assert len(job_saves) == 1
        assert second.job_id == first.job_id == 4242

    def test_a_different_container_is_not_adopted(self, tmp_path, mock_client, rest, mock_send):
        # Same bytes may legitimately be destined for another project; only the recorded target may
        # be resumed into.
        cache = tmp_path / "resume.json"
        _ = self._interrupt(mock_client, rest, mock_send, cache)
        mock_client.save.reset_mock()
        self._setup(rest)
        mock_send.side_effect = None

        _ = upload_files(mock_client, _params("/src/a.txt", container_id=999), resume_cache=cache)

        assert _create_payload(mock_client) is not None
        assert mock_send.call_args.kwargs.get("resume_url") is None


class TestReuseExistingWorkunit:
    def test_does_not_create_workunit(self, mock_client, rest, mock_send):
        # The reused workunit lives in container 777; params still carry the (ignored) create-path 100.
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "upload"})
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip", workunit_id=999))

        assert summary.workunit_id == 999
        assert len(summary.uploads) == 1
        # No workunit was created and its status was never flipped — we don't own a reused workunit.
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        # Dedup + resources target the reused workunit's container/id, resolved via read (not params).
        assert rest.check_duplicates.call_args.args[0] == 777
        assert _checked_names(rest) == ["a.txt"]
        assert rest.create_resources.call_args.args[0] == 999

    def test_not_found_raises(self, mock_client, rest, mock_send):
        mock_client.read.return_value = []

        with pytest.raises(BfabricTransferError, match="not found"):
            upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip", workunit_id=999))

        # Resolution fails before dedup / creation / any transfer.
        rest.check_duplicates.assert_not_called()
        assert _create_payload(mock_client) is None
        mock_send.assert_not_called()

    def test_all_duplicates_skipped_reports_workunit_id(self, mock_client, rest, mock_send):
        # On the reuse path, "all skipped" means the files already live in the targeted workunit, so the
        # summary must report that workunit's id — not None, which reads as "no workunit involved" and is
        # only correct on the create path (where nothing was created).
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.check_duplicates.return_value = _dupes(**{"a.txt": "skip"})

        summary = upload_files(mock_client, _params("/src/a.txt", on_duplicate="skip", workunit_id=999))

        assert summary == UploadSummary(workunit_id=999, skips=[FileSkip(filename="a.txt", category="new")])
        # Nothing created, nothing flipped, no transfer attempted.
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []
        mock_send.assert_not_called()

    def test_all_transfers_fail_does_not_mark_failed(self, mock_client, rest, mock_send):
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")
        mock_send.side_effect = TransferError("down")

        summary = upload_files(mock_client, _params("/src/a.txt", workunit_id=999))

        assert len(summary.uploads) == 0
        assert len(summary.failures) == 1
        # A reused workunit is never flipped to 'failed' — its lifecycle is not ours to change.
        assert _status_updates(mock_client) == []

    def test_setup_failure_does_not_mark_failed_and_reraises(self, mock_client, rest, mock_send):
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.create_resources.side_effect = BfabricTransferError("boom")

        with pytest.raises(BfabricTransferError, match="boom"):
            upload_files(mock_client, _params("/src/a.txt", workunit_id=999))

        assert _status_updates(mock_client) == []


class TestJobTracking:
    def test_creates_job_and_threads_id(self, mock_client, rest, mock_send):
        _distinct_job_id(mock_client, job_id=777)
        rest.create_resources.return_value = _created("a.txt", "b.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", "/src/b.txt", track_job=True))

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

    def test_off_by_default_creates_no_job(self, mock_client, rest, mock_send):
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt"))

        assert _job_payload(mock_client) is None
        assert summary.job_id is None
        assert rest.get_upload_token.call_args.kwargs["job_id"] is None
        sink = mock_send.call_args_list[0].args[0]
        assert "jobId" not in sink.metadata

    def test_on_reuse_path_does_not_touch_workunit(self, mock_client, rest, mock_send):
        _distinct_job_id(mock_client, job_id=888)
        mock_client.read.return_value = [{"container": {"id": 777}}]
        rest.create_resources.return_value = _created("a.txt")
        rest.get_upload_token.return_value = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        summary = upload_files(mock_client, _params("/src/a.txt", workunit_id=999, track_job=True))

        # The job is parented to the reused workunit; the workunit itself is never created or flipped.
        assert _job_payload(mock_client)["parentid"] == 999
        assert summary.job_id == 888
        assert rest.get_upload_token.call_args.kwargs["job_id"] == 888
        assert _create_payload(mock_client) is None
        assert _status_updates(mock_client) == []


class TestParamsValidation:
    def test_workunit_id_and_name_mutually_exclusive(self):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            UploadFilesParams(workunit_id=1, workunit_name="x", files=[UploadFileParam(path=Path("/src/a.txt"))])

    def test_requires_container_and_application_without_id(self):
        with pytest.raises(ValidationError, match="required unless workunit_id"):
            # Missing application_id and no workunit_id.
            UploadFilesParams(container_id=100, files=[UploadFileParam(path=Path("/src/a.txt"))])

    def test_files_are_required(self):
        with pytest.raises(ValidationError, match="files"):
            UploadFilesParams(workunit_id=42)

    def test_workunit_id_alone_is_valid(self):
        params = UploadFilesParams(workunit_id=42, files=[UploadFileParam(path=Path("/src/a.txt"))])
        assert params.workunit_id == 42
        assert params.container_id is None

    def test_on_duplicate_defaults_to_upload(self):
        assert UploadFileParam(path=Path("/src/a.txt")).on_duplicate == "upload"

    def test_unknown_on_duplicate_rejected(self):
        with pytest.raises(ValidationError):
            UploadFileParam(path=Path("/src/a.txt"), on_duplicate="force")
