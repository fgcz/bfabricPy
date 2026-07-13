from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel, model_validator

from bfabric.entities import Job, Workunit
from bfabric.operations.workunit._common import complete_workunit, mark_workunit_failed
from bfabric.transfer import (
    BfabricTransferError,
    Credentials,
    TransferError,
    UploadRestClient,
    check_upload_scope,
    collect_file_infos,
    require_tus,
    send_to_sink,
    tus_sink_for_resource,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bfabric import Bfabric
    from bfabric.transfer import CreatedResource, FileInfo, UploadTokenResult


# --- upload_files: the create-workunit -> dedup -> create-resources -> upload -> register workflow ---

FileProgressCallback = Callable[[str, int, int], None]
"""Called with (filename, bytes_done, total) during a file transfer (absolute ``bytes_done``)."""

UploadStartCallback = Callable[[int, int], None]
"""Called once with (total_files, total_bytes) after dedup, just before the first transfer."""

FileDoneCallback = Callable[[str, bool], None]
"""Called with (filename, success) after each file's transfer finishes (success or failure)."""


class UploadFilesParams(BaseModel):
    """Inputs for :func:`upload_files` (the file list itself is the separate payload argument).

    Either target an existing workunit (``workunit_id``) or create a new one (``container_id`` +
    ``application_id``, optional ``workunit_name``); the two modes are mutually exclusive.
    """

    container_id: int | None = None
    """Container to create the workunit in. Required unless ``workunit_id`` is given."""
    application_id: int | None = None
    """Application the created workunit belongs to. Required unless ``workunit_id`` is given."""
    workunit_id: int | None = None
    """Upload into this existing workunit instead of creating one. Mutually exclusive with ``workunit_name``."""
    workunit_name: str | None = None
    """Name for the created workunit (``None`` → "File upload"); mutually exclusive with ``workunit_id``."""
    force: bool = False
    """Skip the duplicate check and upload every file."""
    import_resources: bool = True
    """Also create B-Fabric import resources."""
    track_job: bool = False
    """Create a ``TUS_UPLOAD`` job under the workunit and attach its id to the upload, so the tus
    server's hooks flip the job to ``DONE``/``FAILED`` as the transfer progresses. Works on both the
    create and reuse paths (the job is a new entity parented to the workunit, so it never mutates a
    reused workunit)."""

    @model_validator(mode="after")
    def _validate_target(self) -> UploadFilesParams:
        if self.workunit_id is not None:
            if self.workunit_name is not None:
                raise ValueError("workunit_name and workunit_id are mutually exclusive.")
        elif self.container_id is None or self.application_id is None:
            raise ValueError("container_id and application_id are required unless workunit_id is given.")
        return self


@dataclass
class FileUpload:
    """A file successfully transferred during :func:`upload_files`."""

    filename: str
    resource_id: int
    storage_path: str
    import_resource_id: int | None = None


@dataclass
class FileFailure:
    """A file whose transfer failed during :func:`upload_files` (the run continues)."""

    filename: str
    resource_id: int
    error: str


@dataclass
class UploadSummary:
    """Outcome of an :func:`upload_files` run."""

    workunit_id: int | None
    uploaded: int
    skipped: int
    failed: int
    uploads: list[FileUpload] = field(default_factory=list)
    failures: list[FileFailure] = field(default_factory=list)
    job_id: int | None = None
    """The tracking job's id when ``track_job`` was set, else ``None``."""


def upload_files(
    client: Bfabric,
    files: Sequence[Path],
    params: UploadFilesParams,
    *,
    on_progress: FileProgressCallback | None = None,
    on_start: UploadStartCallback | None = None,
    on_file_done: FileDoneCallback | None = None,
    audit_attributes: dict[str, str] | None = None,
) -> UploadSummary:
    """Upload files to a B-Fabric workunit over tus, end to end.

    Expands directories, computes checksums, optionally skips duplicates, creates the workunit (or
    reuses an existing one, see ``params.workunit_id``) and its resource records, mints a tus upload
    token, and transfers each file. This is the importable library API behind ``bfabric-cli ...
    upload``; it is the modern replacement for :meth:`bfabric.Bfabric.upload_resource`
    (base64-over-SOAP, small files only).

    Requires ``bfabric[transfer]`` (the tus mover) to be installed. A file whose transfer fails is
    recorded in ``summary.failures`` rather than raised. On any *setup* failure after workunit
    creation -- or if no file transfers successfully -- the workunit is flipped to status ``failed``
    (never deleted, per the operations-module failure-cleanup pattern), so the partial state stays
    diagnosable.

    :param client: a connected client; for the tus transfer it must be OAuth-backed with the ``tus``
        scope (a fail-fast :class:`~bfabric.transfer.ScopeError` is raised otherwise).
    :param files: files and/or directories to upload; directories are expanded recursively, keeping
        their relative path as the resource name.
    :param params: the target workunit -- either an existing ``workunit_id`` or a
        ``container_id``/``application_id`` to create one under -- plus ``force`` /
        ``import_resources`` / ``track_job`` (see :class:`UploadFilesParams`).
    :param on_progress: optional ``(filename, bytes_done, total)`` per-chunk progress callback.
    :param on_start: optional ``(total_files, total_bytes)`` callback fired once after dedup, just
        before the first transfer (never fired when everything is skipped as a duplicate).
    :param on_file_done: optional ``(filename, success)`` callback fired after each file's transfer,
        for successes and failures alike.
    :param audit_attributes: written verbatim as workunit custom attributes.
    :returns: an :class:`UploadSummary`; its ``workunit_id`` is the created or reused workunit, and is
        ``None`` only on the create path when every file was skipped as a duplicate (nothing was
        created). Setup failures raise :class:`~bfabric.transfer.BfabricTransferError`.
    """
    # Fail fast (before creating a workunit) if the tus mover, an OAuth client, or the 'tus' scope is
    # missing, so a missing dependency / wrong auth / scope-less token never leaves an orphaned
    # 'failed' workunit behind. (The scope is also re-checked at initiate time for direct
    # UploadRestClient callers.)
    require_tus()
    rest = UploadRestClient(client)
    check_upload_scope(client)
    file_infos = collect_file_infos(list(files))

    # Resolve the target container up front: it feeds both the duplicate check and the tus sink
    # metadata. On the reuse path it comes from the existing workunit, not from params.
    container_id = _resolve_container_id(client, params)

    to_upload, skipped = _select_files_to_upload(rest, file_infos, params, container_id)
    if not to_upload:
        logger.info("Nothing to upload (all {} file(s) skipped as duplicates).", skipped)
        # workunit_id is None on the create path (nothing was created) but the reused id on the reuse
        # path -- the caller's files provably already live there, so don't report "no workunit".
        return UploadSummary(workunit_id=params.workunit_id, uploaded=0, skipped=skipped, failed=0)

    if on_start is not None:
        on_start(len(to_upload), sum(fi.size for fi in to_upload))

    # Only own the workunit lifecycle (status transitions, failure cleanup) for workunits we create;
    # a caller-supplied `workunit_id` targets a pre-existing workunit we must not flip or fail.
    if params.workunit_id is not None:
        workunit_id = params.workunit_id
        created = False
    else:
        workunit_id = _create_upload_workunit(client=client, params=params, audit_attributes=audit_attributes or {})
        created = True
    job_id: int | None = None
    try:
        # Create the tracking job before minting the token, so its id is baked into both the token
        # request and every sink's metadata (the server hooks key off that jobId to update status).
        if params.track_job:
            job_id = _create_upload_job(client, workunit_id)
        resources = rest.create_resources(workunit_id, to_upload, create_import_resources=params.import_resources)
        resources_by_name = _pair_resources_to_files(resources, to_upload)
        import_resource_ids = [r.import_resource_id for r in resources if r.import_resource_id is not None]
        token_result = rest.get_upload_token(workunit_id, [r.id for r in resources], import_resource_ids, job_id=job_id)
        uploads, failures = _transfer_files(
            to_upload,
            resources_by_name,
            token_result,
            workunit_id=workunit_id,
            container_id=container_id,
            job_id=job_id,
            on_progress=on_progress,
            on_file_done=on_file_done,
        )
    except BaseException:
        # Mark the workunit failed (do NOT delete) so the partial state is diagnosable — see the
        # "Failure cleanup pattern" in operations_module.md.
        if created:
            mark_workunit_failed(client, workunit_id)
        raise

    if not uploads:
        # Every transfer failed: the workunit has no usable content, so flip it to failed (kept, not
        # deleted). The per-file errors are returned for the caller to inspect.
        if created:
            mark_workunit_failed(client, workunit_id)
    elif created:
        # Intentionally outside the try/except above: the bytes have already landed, so a failure of
        # this final status flip should surface as-is rather than mark a workunit-with-real-content
        # 'failed'. It stays 'processing' and the exception propagates for the caller to retry.
        _ = complete_workunit(client=client, workunit_id=workunit_id)
    return UploadSummary(
        workunit_id=workunit_id,
        uploaded=len(uploads),
        skipped=skipped,
        failed=len(failures),
        uploads=uploads,
        failures=failures,
        job_id=job_id,
    )


def _resolve_container_id(client: Bfabric, params: UploadFilesParams) -> int:
    """The container the upload targets: from ``params`` on the create path, else the reused workunit's."""
    if params.workunit_id is None:
        # Guaranteed non-None on the create path by UploadFilesParams._validate_target.
        assert params.container_id is not None
        return params.container_id
    return _existing_workunit_container_id(client, params.workunit_id)


def _existing_workunit_container_id(client: Bfabric, workunit_id: int) -> int:
    result = client.read("workunit", {"id": workunit_id})
    if not result:
        raise BfabricTransferError(f"Workunit {workunit_id} not found; cannot upload into it.")
    container = result[0].get("container")
    container_id = container["id"] if isinstance(container, Mapping) else None
    if not isinstance(container_id, int):
        raise BfabricTransferError(f"Workunit {workunit_id} has no usable container id.")
    return container_id


def _select_files_to_upload(
    rest: UploadRestClient, file_infos: list[FileInfo], params: UploadFilesParams, container_id: int
) -> tuple[list[FileInfo], int]:
    if params.force:
        return file_infos, 0
    results = rest.check_duplicates(container_id, file_infos)
    # Guard against a name-normalization mismatch silently dropping a file: every input file must get
    # a verdict, otherwise a file the server didn't recognise would be miscounted as skipped and never
    # uploaded (silent data loss reported as success).
    verdict_names = {r.filename for r in results}
    unaccounted = sorted(fi.name for fi in file_infos if fi.name not in verdict_names)
    if unaccounted:
        raise BfabricTransferError(
            "check-duplicates returned no verdict for: "
            + ", ".join(unaccounted)
            + " (name mismatch between the request and response); refusing to upload to avoid silently "
            "dropping files. Re-run with force=True to bypass the duplicate check."
        )
    # Only "upload" (new file) and "skip" (exact duplicate already stored) are actionable here. Any
    # other verdict -- notably "link", where the server wants a link to content-identical bytes rather
    # than a re-upload -- is not implemented by upload_files; folding it into the skipped count would
    # silently fail to register a file the user asked for. Fail loud instead.
    unsupported = sorted(r.filename for r in results if r.action not in ("upload", "skip"))
    if unsupported:
        raise BfabricTransferError(
            "check-duplicates requested an unsupported action (e.g. 'link') for: "
            + ", ".join(unsupported)
            + "; these are content-duplicates the server wants registered as links, which upload_files "
            "does not support. Re-run with force=True to upload them as new resources."
        )
    upload_names = {r.filename for r in results if r.action == "upload"}
    to_upload = [fi for fi in file_infos if fi.name in upload_names]
    return to_upload, len(file_infos) - len(to_upload)


def _create_upload_workunit(client: Bfabric, params: UploadFilesParams, audit_attributes: dict[str, str]) -> int:
    # An empty workunit (resources are created separately via the REST create-resources call), so we
    # cannot reuse create_workunit, which requires at least one resource/parameter/link.
    # Only reached on the create path, where the validator guarantees container/application are set.
    assert params.container_id is not None and params.application_id is not None
    result = client.save(
        "workunit",
        {
            "containerid": params.container_id,
            "applicationid": params.application_id,
            "name": params.workunit_name or "File upload",
            "status": "processing",
            "customattribute": [{"name": key, "value": value} for key, value in audit_attributes.items()],
        },
    )
    return Workunit(result[0], client=None, bfabric_instance=client.config.base_url).id


def _create_upload_job(client: Bfabric, workunit_id: int) -> int:
    """Create the ``TUS_UPLOAD`` tracking job parented to ``workunit_id`` and return its id.

    The job starts at status ``NEW``; the tus server's own hooks move it to ``DONE``/``FAILED`` once
    the transfer runs, so nothing here mutates its status afterwards.
    """
    result = client.save(
        "job",
        {"action": "TUS_UPLOAD", "status": "NEW", "parentclassname": "Workunit", "parentid": workunit_id},
    )
    return Job(result[0], client=None, bfabric_instance=client.config.base_url).id


def _pair_resources_to_files(resources: list[CreatedResource], to_upload: list[FileInfo]) -> dict[str, CreatedResource]:
    # Pair each file to its resource by NAME, not list position: create-resources is not guaranteed
    # to preserve request order, and index-pairing would upload one file's bytes to another's path.
    # Name-pairing only works if names are unique, so reject duplicates up front — otherwise two files
    # sharing a resource name would silently collapse into one resource (data loss).
    name_counts = Counter(fi.name for fi in to_upload)
    duplicate_names = sorted(name for name, count in name_counts.items() if count > 1)
    if duplicate_names:
        raise BfabricTransferError(
            "Cannot upload multiple files that map to the same resource name: "
            + ", ".join(duplicate_names)
            + " (name-based pairing cannot disambiguate them)."
        )
    if len(resources) != len(to_upload):
        raise BfabricTransferError(
            f"create-resources returned {len(resources)} resource(s) for {len(to_upload)} file(s); "
            "cannot reliably pair files to resources."
        )
    by_name = {r.name: r for r in resources}
    missing = [fi.name for fi in to_upload if fi.name not in by_name]
    if missing:
        raise BfabricTransferError("create-resources returned no resource for: " + ", ".join(missing))
    return by_name


def _transfer_files(
    to_upload: list[FileInfo],
    resources_by_name: dict[str, CreatedResource],
    token_result: UploadTokenResult,
    *,
    workunit_id: int,
    container_id: int,
    job_id: int | None = None,
    on_progress: FileProgressCallback | None,
    on_file_done: FileDoneCallback | None = None,
) -> tuple[list[FileUpload], list[FileFailure]]:
    """Transfer each file over tus, recording per-file success/failure.

    A :class:`~bfabric.transfer.TransferError` is recorded and the run continues; any other exception
    propagates so a genuine bug is not silently logged as a flaky upload. ``on_file_done`` fires once
    per file either way, so a caller-side progress counter still reaches the total when files fail.
    """
    uploads: list[FileUpload] = []
    failures: list[FileFailure] = []
    creds = Credentials()  # the tus leg authenticates with the sink's own token, not an access token
    for file_info in to_upload:
        resource = resources_by_name[file_info.name]
        sink = tus_sink_for_resource(
            resource, token_result, workunit_id=workunit_id, container_id=container_id, job_id=job_id
        )
        file_progress = _make_file_progress(on_progress, file_info.name)
        try:
            _ = send_to_sink(sink, file_info.path, creds, on_progress=file_progress)
        except TransferError as error:
            logger.warning("Upload failed for {}: {}", file_info.name, error)
            failures.append(FileFailure(filename=file_info.name, resource_id=resource.id, error=str(error)))
            if on_file_done is not None:
                on_file_done(file_info.name, False)
            continue
        uploads.append(
            FileUpload(
                filename=file_info.name,
                resource_id=resource.id,
                storage_path=resource.storage_path or "",
                import_resource_id=resource.import_resource_id,
            )
        )
        if on_file_done is not None:
            on_file_done(file_info.name, True)
    return uploads, failures


def _make_file_progress(on_progress: FileProgressCallback | None, filename: str) -> Callable[[int, int], None] | None:
    if on_progress is None:
        return None

    def _report(done: int, total: int) -> None:
        on_progress(filename, done, total)

    return _report
