from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
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
    from collections.abc import Collection, Sequence
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
    link_duplicates: bool = False
    """Register a duplicate as a link to the already-stored bytes instead of skipping it, so the
    workunit gets a resource for every input file without re-transferring content the instance
    already holds. Applies to any verdict naming an ``existingResourceId`` -- in practice a
    ``skip`` on an ``exact_duplicate`` / ``renamed_duplicate``. Off by default: linking creates a
    resource pointing at bytes this caller never uploaded, so it is an explicit opt-in. Has no effect
    together with ``force``, which skips the duplicate check and so produces no verdicts to act on."""
    track_job: bool = False
    """Create a ``UPLOAD`` job under the workunit and attach its id to the upload, so the tus
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
    """Files whose bytes were transferred."""
    skipped: int
    """Duplicates the check reported as already stored; no resource was created for them."""
    failed: int
    uploads: list[FileUpload] = field(default_factory=list)
    failures: list[FileFailure] = field(default_factory=list)
    linked: list[FileUpload] = field(default_factory=list)
    """Files registered as links to already-stored bytes: a resource exists, but nothing was
    transferred. Distinct from ``skipped``, where no resource was created at all."""
    job_id: int | None = None
    """The tracking job's id when ``track_job`` was set, else ``None``."""

    @property
    def linked_count(self) -> int:
        """Number of files registered as links (the counterpart to ``uploaded`` for ``linked``)."""
        return len(self.linked)


def upload_files(
    client: Bfabric,
    files: Sequence[Path],
    params: UploadFilesParams,
    *,
    on_progress: FileProgressCallback | None = None,
    on_start: UploadStartCallback | None = None,
    on_file_done: FileDoneCallback | None = None,
    audit_attributes: dict[str, str] | None = None,
    exclude_names: Collection[str] | None = None,
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
        ``track_job`` (see :class:`UploadFilesParams`).
    :param on_progress: optional ``(filename, bytes_done, total)`` per-chunk progress callback.
    :param on_start: optional ``(total_files, total_bytes)`` callback fired once after dedup, just
        before the first transfer (never fired when everything is skipped as a duplicate). It reports
        the post-dedup file set, which is decided before ``create-resources`` runs: should the server
        register some of those as links, fewer files than announced are actually transferred.
    :param on_file_done: optional ``(filename, success)`` callback fired after each file's transfer,
        for successes and failures alike.
    :param audit_attributes: written verbatim as workunit custom attributes.
    :param exclude_names: basenames to skip at any depth (e.g. a sentinel file the caller drops in
        the folder, or ``.DS_Store``). Filter here rather than pre-filtering ``files`` yourself: a
        flat file list loses the directory that gives nested files their relative resource name.
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
    file_infos = collect_file_infos(list(files), exclude_names=exclude_names)

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
        resources = rest.create_resources(workunit_id, to_upload)
        resources_by_name = _pair_resources_to_files(resources, to_upload)
        # A linked resource already points at stored bytes and is created AVAILABLE, so it must be kept
        # out of both the token request and the transfer loop; sending it would push bytes for a
        # resource the server never expects an upload for.
        transferable = [fi for fi in to_upload if not resources_by_name[fi.name].linked]
        linked = [
            _as_file_upload(fi.name, resource) for fi in to_upload if (resource := resources_by_name[fi.name]).linked
        ]
        if linked:
            logger.info("{} file(s) registered as links to existing content; not transferring them.", len(linked))
        uploads: list[FileUpload] = []
        failures: list[FileFailure] = []
        if transferable:
            pending = [resources_by_name[fi.name] for fi in transferable]
            import_resource_ids = [r.import_resource_id for r in pending if r.import_resource_id is not None]
            token_result = rest.get_upload_token(
                workunit_id, [r.id for r in pending], import_resource_ids, job_id=job_id
            )
            uploads, failures = _transfer_files(
                transferable,
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

    if not uploads and not linked:
        # Every transfer failed: the workunit has no usable content, so flip it to failed (kept, not
        # deleted). The per-file errors are returned for the caller to inspect. Linked resources are
        # already AVAILABLE, so a run that only linked has real content despite transferring nothing.
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
        linked=linked,
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
    # "upload" (new file) and "skip" (exact duplicate already stored) are always actionable; "link"
    # (content-identical bytes already stored elsewhere) only when the caller opted in. Any other
    # verdict is one we cannot act on, and folding it into the skipped count would silently fail to
    # register a file the user asked for. Fail loud instead.
    supported = ("upload", "skip", "link") if params.link_duplicates else ("upload", "skip")
    unsupported = sorted(r.filename for r in results if r.action not in supported)
    if unsupported:
        # Point at link_duplicates only when 'link' is actually what we refused; any other verdict is
        # one this client has no handling for at all, so force=True is the only way forward.
        refused_link = any(r.action == "link" for r in results if r.filename in set(unsupported))
        hint = (
            "; these are content-duplicates the server wants registered as links. Re-run with "
            "link_duplicates=True to register them as links, or force=True to upload them as new resources."
            if refused_link
            else "; upload_files cannot act on this verdict. Re-run with force=True to upload them as new resources."
        )
        raise BfabricTransferError(
            "check-duplicates requested an unsupported action for: " + ", ".join(unsupported) + hint
        )

    # Which files to link rather than transfer. A content-duplicate arrives as action "skip" with an
    # existingResourceId (category exact_duplicate / renamed_duplicate) -- the server does not use
    # action "link" for it -- so linking is driven by a skip verdict that names a resource to link to.
    # An explicit "link" action is honoured too, for a server that does emit it.
    # A skip without an existingResourceId has no link target, so it stays a plain skip.
    link_ids: dict[str, int] = {}
    if params.link_duplicates:
        link_ids = {
            r.filename: r.resource_id for r in results if r.action in ("skip", "link") and r.resource_id is not None
        }

    # An explicit "link" verdict with no id is unusable: we can neither link nor safely fall back to
    # uploading (the server already told us not to), so fail loud rather than silently drop the file.
    unusable = sorted(r.filename for r in results if r.action == "link" and r.resource_id is None)
    if unusable:
        raise BfabricTransferError(
            "check-duplicates returned a 'link' verdict without an existingResourceId for: "
            + ", ".join(unusable)
            + "; cannot register a link without it. Re-run with force=True to upload them as new resources."
        )

    upload_names = {r.filename for r in results if r.action == "upload"}
    to_upload = [
        replace(fi, link_from_resource_id=link_ids[fi.name]) if fi.name in link_ids else fi
        for fi in file_infos
        if fi.name in upload_names or fi.name in link_ids
    ]
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
    """Create the ``UPLOAD`` tracking job parented to ``workunit_id`` and return its id.

    The job starts at status ``NEW``; the tus server's own hooks move it to ``DONE``/``FAILED`` once
    the transfer runs, so nothing here mutates its status afterwards.
    """
    result = client.save(
        "job",
        {"action": "UPLOAD", "status": "NEW", "parentclassname": "Workunit", "parentid": workunit_id},
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
        uploads.append(_as_file_upload(file_info.name, resource))
        if on_file_done is not None:
            on_file_done(file_info.name, True)
    return uploads, failures


def _as_file_upload(filename: str, resource: CreatedResource) -> FileUpload:
    return FileUpload(
        filename=filename,
        resource_id=resource.id,
        storage_path=resource.storage_path or "",
        import_resource_id=resource.import_resource_id,
    )


def _make_file_progress(on_progress: FileProgressCallback | None, filename: str) -> Callable[[int, int], None] | None:
    if on_progress is None:
        return None

    def _report(done: int, total: int) -> None:
        on_progress(filename, done, total)

    return _report
