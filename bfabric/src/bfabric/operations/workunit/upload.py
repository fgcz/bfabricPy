from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from loguru import logger
from pydantic import BaseModel, model_validator

from bfabric.entities import Job, Workunit
from bfabric.operations.workunit._common import complete_workunit, mark_workunit_failed
from bfabric.transfer import (
    BfabricTransferError,
    CreatedResource,
    Credentials,
    TransferError,
    UploadRestClient,
    check_upload_scope,
    collect_file_infos,
    require_tus,
    send_to_sink,
    tus_sink_for_resource,
)
from bfabric.transfer._generic.origin import same_origin
from bfabric.transfer.resume_cache import ResumeCache, ResumeEntry, compute_resume_cache_path

if TYPE_CHECKING:
    from collections.abc import Collection

    from bfabric import Bfabric
    from bfabric.transfer import DuplicateResult, FileInfo, TransferSinkTus, UploadTokenResult


# --- upload_files: the create-workunit -> dedup -> create-resources -> upload -> register workflow ---

FileProgressCallback = Callable[[str, int, int], None]
"""Called with (filename, bytes_done, total) during a file transfer (absolute ``bytes_done``)."""

UploadStartCallback = Callable[[int, int], None]
"""Called once with (total_files, total_bytes) after dedup, just before the first transfer."""

FileDoneCallback = Callable[[str, bool], None]
"""Called with (filename, success) after each file's transfer finishes (success or failure)."""

FileUrlCallback = Callable[[str, str], None]
"""Called with (filename, upload_url) as soon as a file's resumable tus URL is known."""

_USE_DEFAULT_RESUME_CACHE: Final = Path("<default>")
"""Sentinel for ``resume_cache``: resume via the per-server default path.

A plain ``None`` default cannot express this -- ``None`` already means "keep no state", which a
caller must still be able to ask for.
"""

OnDuplicate = Literal["upload", "skip", "link"]
"""What to do with a file whose content the target container already stores.

Named after the server's own ``check-duplicates`` verdicts (``DuplicateResult.action``), so a
caller's intent and the server's answer are the same three words.
"""


class UploadFileParam(BaseModel):
    """One file or directory to upload, and what to do if B-Fabric already stores its content."""

    path: Path
    on_duplicate: OnDuplicate = "upload"
    """``upload`` sends the file regardless (no duplicate check is made for it), ``skip`` leaves it
    out of the workunit entirely, ``link`` registers a resource pointing at the already-stored bytes
    without transferring any. A directory applies its policy to every file under it.

    ``link`` only links to a duplicate the server reports as ``linkable``; one whose resource is
    still ``pending`` or ``failed`` has no bytes to link to, so that file is uploaded instead. It
    needs a B-Fabric that reports ``linkable`` on ``check-duplicates``."""


class UploadFilesParams(BaseModel):
    """Inputs for :func:`upload_files`.

    Either target an existing workunit (``workunit_id``) or create a new one (``container_id`` +
    ``application_id``, optional ``workunit_name``); the two modes are mutually exclusive.
    """

    files: list[UploadFileParam]
    """The files and/or directories to upload, each with its own duplicate policy."""
    container_id: int | None = None
    """Container to create the workunit in. Required unless ``workunit_id`` is given."""
    application_id: int | None = None
    """Application the created workunit belongs to. Required unless ``workunit_id`` is given."""
    workunit_id: int | None = None
    """Upload into this existing workunit instead of creating one. Mutually exclusive with ``workunit_name``."""
    workunit_name: str | None = None
    """Name for the created workunit (``None`` → "File upload"); mutually exclusive with ``workunit_id``."""
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
    """A file whose bytes were transferred during :func:`upload_files`.

    This records a completed *transfer*, not verified storage. The storage service runs its checks
    (virus scan, checksum verification, disk state) in a post-finish hook once the tus transfer is
    already complete, and that hook reports back to B-Fabric rather than to the uploading client --
    it cannot fail the transfer that produced it. A file recorded here may therefore end up with its
    resource marked ``failed``, holding no usable bytes.

    Re-read ``resource_id``'s status before treating the file as safely stored -- in particular
    before deleting the local copy. See :func:`upload_files` for the full contract.
    """

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
class FileSkip:
    """A file left out of the workunit because the container already stores its content."""

    filename: str
    category: str
    """The server's duplicate classification, e.g. ``exact_duplicate`` / ``renamed_duplicate``."""
    existing_resource_id: int | None = None
    """The resource already holding these bytes, when the verdict named one."""


@dataclass
class UploadSummary:
    """Outcome of an :func:`upload_files` run: one list per outcome, so ``len()`` gives the counts."""

    workunit_id: int | None
    uploads: list[FileUpload] = field(default_factory=list)
    """Files whose bytes were transferred -- not files confirmed stored.

    Success here means the tus transfer completed, which is everything the client can observe. The
    storage service's post-finish checks run afterwards and report to B-Fabric, so a file listed here
    can still end up ``failed``. See :class:`FileUpload`."""
    skips: list[FileSkip] = field(default_factory=list)
    """Duplicates the check reported as already stored; no resource was created for them."""
    failures: list[FileFailure] = field(default_factory=list)
    links: list[FileUpload] = field(default_factory=list)
    """Files registered as links to already-stored bytes: a resource exists, but nothing was
    transferred. Distinct from ``skips``, where no resource was created at all."""
    job_id: int | None = None
    """The tracking job's id when ``track_job`` was set, else ``None``."""


class WorkunitCompletionError(BfabricTransferError):
    """The upload finished but the workunit's final status flip failed.

    Carries the :class:`UploadSummary` of the completed transfers, so a caller can record what
    actually landed and retry only the status flip instead of re-uploading or creating a second
    workunit. The workunit is left ``processing`` (never ``failed``): its bytes are real.
    """

    def __init__(self, message: str, summary: UploadSummary) -> None:
        super().__init__(message)
        self.summary: UploadSummary = summary


def upload_files(
    client: Bfabric,
    params: UploadFilesParams,
    *,
    on_progress: FileProgressCallback | None = None,
    on_start: UploadStartCallback | None = None,
    on_file_done: FileDoneCallback | None = None,
    on_url: FileUrlCallback | None = None,
    audit_attributes: dict[str, str] | None = None,
    exclude_names: Collection[str] | None = None,
    resume_cache: Path | None = _USE_DEFAULT_RESUME_CACHE,
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

    **A successful return does not mean the files are stored.** It means every transfer completed,
    which is the last thing this client can observe. The storage service then runs its own checks
    (virus scan, checksum verification, disk state) in a post-finish hook, and that hook reports to
    B-Fabric rather than to the uploader: the tus transfer is already complete by then, so there is
    no channel to fail it through. A resource can therefore be marked ``failed`` after this function
    has reported it in ``summary.uploads`` -- and the workunit is flipped to ``available`` on the
    same unverified basis, so its status is not confirmation either.

    A caller that deletes its local copy once B-Fabric holds the data (an instrument feeder, say)
    must therefore re-read each ``FileUpload.resource_id``'s status and require ``available`` before
    deleting -- never treat this function's return as that confirmation. The check belongs at
    deletion time rather than here: verification runs on the server's schedule, and the answer that
    matters is the resource's state when the delete decision is made, not moments after the upload.

    :param client: a connected client; for the tus transfer it must be OAuth-backed with the ``tus``
        scope (a fail-fast :class:`~bfabric.transfer.ScopeError` is raised otherwise).
    :param params: the ``files`` to upload (each with its own ``on_duplicate`` policy; directories
        are expanded recursively, keeping their relative path as the resource name) and the target
        workunit -- either an existing ``workunit_id`` or a ``container_id``/``application_id`` to
        create one under (see :class:`UploadFilesParams`).
    :param on_progress: optional ``(filename, bytes_done, total)`` per-chunk progress callback.
    :param on_start: optional ``(total_files, total_bytes)`` callback fired once after dedup, just
        before the first transfer (never fired when everything is skipped as a duplicate). It reports
        the post-dedup file set, which is decided before ``create-resources`` runs: should the server
        register some of those as links, fewer files than announced are actually transferred.
    :param on_file_done: optional ``(filename, success)`` callback fired after each file's transfer,
        for successes and failures alike.
    :param on_url: optional ``(filename, upload_url)`` callback fired once per transferred file, as
        soon as its resumable tus URL exists -- including for a file whose transfer then fails, which
        is the case the URL is worth keeping for. Pass ``resume_cache`` to have ``upload_files``
        persist and reuse these itself; this callback is for a caller keeping its own ledger besides.
        Not fired for linked or skipped files (nothing is sent).
    :param audit_attributes: written verbatim as workunit custom attributes.
    :param resume_cache: path to a JSON file in which each interrupted transfer's resumable tus URL
        is kept, keyed by the file's MD5 and source path, so a later run continues it instead of
        re-sending from byte 0. Both halves matter: a failed acquisition writes the same bytes every
        time, so MD5 alone would collapse two distinct measurements onto one resource. Left
        unset, a per-server path under ``~/.bfabric/resume`` is used, so an interrupted upload is
        resumable without the caller arranging anything; ``None`` keeps no state and never resumes.
        A resumed file continues into its original workunit and resource -- a tus URL's metadata is
        fixed when the upload is created, so its bytes cannot be redirected to a new one. An entry is
        dropped once its file transfers, and ignored when it is stale, past its TTL, no longer
        same-origin with the tus endpoint, or was stored for a different container/application -- in
        each of those cases the file is uploaded afresh.
    :param exclude_names: basenames to skip at any depth (e.g. a sentinel file the caller drops in
        the folder, or ``.DS_Store``). Filter here rather than pre-filtering ``files`` yourself: a
        flat file list loses the directory that gives nested files their relative resource name.
    :returns: an :class:`UploadSummary` recording which files transferred, were linked, were skipped
        and failed -- transfer outcomes, not storage confirmations (see above). Its ``workunit_id`` is
        the created or reused workunit, and is ``None`` only on the create path when every file was
        skipped as a duplicate (nothing was created). Setup failures raise
        :class:`~bfabric.transfer.BfabricTransferError`.
    :raises WorkunitCompletionError: if every transfer succeeded but marking the created workunit
        ``available`` failed. It carries the ``UploadSummary`` of what landed, so the caller can
        retry only that status flip rather than re-uploading into a second workunit.
    """
    # Fail fast (before creating a workunit) if the tus mover, an OAuth client, or the 'tus' scope is
    # missing, so a missing dependency / wrong auth / scope-less token never leaves an orphaned
    # 'failed' workunit behind. (The scope is also re-checked at initiate time for direct
    # UploadRestClient callers.)
    require_tus()
    rest = UploadRestClient(client)
    check_upload_scope(client)
    file_infos, policies = _collect_entries(params, exclude_names)

    # Resolve the target container up front: it feeds both the duplicate check and the tus sink
    # metadata. On the reuse path it comes from the existing workunit, not from params.
    container_id = _resolve_container_id(client, params)

    to_upload, skips = _select_files_to_upload(rest, file_infos, policies, container_id)
    if not to_upload:
        logger.info("Nothing to upload (all {} file(s) skipped as duplicates).", len(skips))
        # workunit_id is None on the create path (nothing was created) but the reused id on the reuse
        # path -- the caller's files provably already live there, so don't report "no workunit".
        return UploadSummary(workunit_id=params.workunit_id, skips=skips)

    if on_start is not None:
        on_start(len(to_upload), sum(fi.size for fi in to_upload))

    resume_path = (
        compute_resume_cache_path(str(client.config.base_url)).expanduser()
        if resume_cache is _USE_DEFAULT_RESUME_CACHE
        else resume_cache
    )
    cache = ResumeCache(resume_path) if resume_path is not None else None
    # Decided before anything is created: a tus URL's metadata is fixed at creation, so a file with a
    # saved URL must continue into its ORIGINAL workunit and resource. Creating a second pair and then
    # resuming the old URL would send the bytes to the first resource while reporting the second.
    adopted = _adopted_uploads(cache, to_upload, params, container_id)

    # Only own the workunit lifecycle (status transitions, failure cleanup) for workunits we create;
    # a caller-supplied `workunit_id` targets a pre-existing workunit we must not flip or fail.
    if params.workunit_id is not None:
        workunit_id = params.workunit_id
        created = False
    elif adopted:
        # Continuing an interrupted run: its workunit already exists and is still 'processing'.
        workunit_id = next(iter(adopted.values())).workunit_id
        created = True
        logger.info("Resuming interrupted upload into workunit {}.", workunit_id)
    else:
        workunit_id = _create_upload_workunit(client=client, params=params, audit_attributes=audit_attributes or {})
        created = True
    # An adopted run keeps the original job: the hooks key status off jobId, and the saved URL's tus
    # metadata still names the first run's job, so a second one would leave the first hanging with
    # nothing to move it to a terminal state.
    job_id: int | None = _adopted_job_id(adopted)
    try:
        # Create the tracking job before minting the token, so its id is baked into both the token
        # request and every sink's metadata (the server hooks key off that jobId to update status).
        if params.track_job and job_id is None:
            job_id = _create_upload_job(client, workunit_id)
        # create-resources only ever creates, so an adopted file must not go through it: its resource
        # already exists and is the one its saved tus URL points at.
        to_create = [fi for fi in to_upload if fi.name not in adopted]
        resources_by_name = _adopted_resources(adopted, to_upload)
        if to_create:
            resources = rest.create_resources(workunit_id, to_create)
            resources_by_name |= _pair_resources_to_files(resources, to_create)
        # A linked resource already points at stored bytes and is created AVAILABLE, so it must be kept
        # out of both the token request and the transfer loop; sending it would push bytes for a
        # resource the server never expects an upload for.
        transferable = [fi for fi in to_upload if not resources_by_name[fi.name].linked]
        links = [
            _as_file_upload(fi.name, resource) for fi in to_upload if (resource := resources_by_name[fi.name]).linked
        ]
        if links:
            logger.info("{} file(s) registered as links to existing content; not transferring them.", len(links))
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
                adopted=adopted,
                workunit_id=workunit_id,
                container_id=container_id,
                job_id=job_id,
                on_progress=on_progress,
                on_file_done=on_file_done,
                on_url=on_url,
                resume_cache=cache,
                application_id=params.application_id,
            )
    except BaseException:
        # Mark the workunit failed (do NOT delete) so the partial state is diagnosable — see the
        # "Failure cleanup pattern" in operations_module.md.
        if created:
            mark_workunit_failed(client, workunit_id)
        raise

    if not uploads and not links and created and not _has_resumable(cache, to_upload, params, container_id):
        # Every transfer failed: the workunit has no usable content, so flip it to failed (kept, not
        # deleted). The per-file errors are returned for the caller to inspect. Linked resources are
        # already AVAILABLE, so a run that only linked has real content despite transferring nothing.
        # An interrupted transfer that saved a resume URL is exempt: it is unfinished, not failed, and
        # the next run continues into this very workunit. Its resources stay 'pending' until then, and
        # B-Fabric's own cleanup reclaims them if that run never comes.
        mark_workunit_failed(client, workunit_id)
    summary = UploadSummary(
        workunit_id=workunit_id,
        uploads=uploads,
        skips=skips,
        failures=failures,
        links=links,
        job_id=job_id,
    )
    if (uploads or links) and created:
        # Intentionally outside the try/except above: the bytes have already landed, so a failure of
        # this final status flip must not mark a workunit-with-real-content 'failed'. It stays
        # 'processing' and the error propagates -- but as a WorkunitCompletionError carrying the
        # summary, so the caller can record what transferred and retry only the flip.
        try:
            _ = complete_workunit(client=client, workunit_id=workunit_id)
        except BaseException as error:
            raise WorkunitCompletionError(
                f"Upload to workunit {workunit_id} succeeded but marking it 'available' failed: {error}",
                summary,
            ) from error
    return summary


def _adopted_uploads(
    cache: ResumeCache | None,
    to_upload: list[FileInfo],
    params: UploadFilesParams,
    container_id: int,
) -> dict[str, ResumeEntry]:
    """The saved interrupted uploads to continue, keyed by resource name.

    Keyed by name rather than MD5 because MD5 is not unique within a run -- a failed acquisition
    writes the same bytes every time, which is why the cache itself keys on ``(md5, path)`` -- and
    two files sharing one would otherwise collapse onto a single resource. Names are already
    guaranteed unique by ``_reject_duplicate_names``.

    Only meaningful on the create path: a caller-supplied ``workunit_id`` names the target
    explicitly, so there is nothing to adopt. All adopted files must share one workunit -- a run
    writes into a single workunit -- so entries naming any other one are ignored and those files are
    uploaded afresh.
    """
    if cache is None or params.workunit_id is not None:
        return {}
    found: dict[str, ResumeEntry] = {}
    for file_info in to_upload:
        entry = cache.lookup(
            md5=file_info.md5,
            path=str(file_info.path),
            container_id=container_id,
            application_id=params.application_id,
        )
        if entry is not None:
            found[file_info.name] = entry
    if not found:
        return {}
    workunit_id = next(iter(found.values())).workunit_id
    kept = {name: entry for name, entry in found.items() if entry.workunit_id == workunit_id}
    if len(kept) != len(found):
        logger.info(
            "Ignoring {} resume entry/entries naming a different workunit; those files upload afresh.",
            len(found) - len(kept),
        )
    return kept


def _adopted_job_id(adopted: Mapping[str, ResumeEntry]) -> int | None:
    """The tracking job the adopted uploads were started under, if they agree on one."""
    job_ids = {entry.job_id for entry in adopted.values() if entry.job_id is not None}
    return job_ids.pop() if len(job_ids) == 1 else None


def _adopted_resources(adopted: Mapping[str, ResumeEntry], to_upload: list[FileInfo]) -> dict[str, CreatedResource]:
    """Rebuild the ``CreatedResource`` records for adopted files from their cache entries.

    The originals came from a previous run's ``create-resources``; only the ids and storage path are
    needed downstream, and the saved tus URL already carries the rest.
    """
    return {
        fi.name: CreatedResource(id=entry.resource_id, name=fi.name, storagePath=entry.storage_path)
        for fi in to_upload
        if (entry := adopted.get(fi.name)) is not None
    }


def _has_resumable(
    cache: ResumeCache | None,
    to_upload: list[FileInfo],
    params: UploadFilesParams,
    container_id: int,
) -> bool:
    """Whether any file left a resume URL behind, making this workunit worth keeping for a retry."""
    if cache is None:
        return False
    return any(
        cache.lookup(md5=fi.md5, path=str(fi.path), container_id=container_id, application_id=params.application_id)
        is not None
        for fi in to_upload
    )


def _collect_entries(
    params: UploadFilesParams, exclude_names: Collection[str] | None
) -> tuple[list[FileInfo], dict[str, OnDuplicate]]:
    """Every file to consider, in input order, plus the ``on_duplicate`` of the entry each came from.

    The collector is called per entry because it flattens directories, losing which entry a file came
    from -- and that is what carries the policy.
    """
    file_infos: list[FileInfo] = []
    policies: dict[str, OnDuplicate] = {}
    for entry in params.files:
        for file_info in collect_file_infos([entry.path], exclude_names=exclude_names):
            file_infos.append(file_info)
            policies[file_info.name] = entry.on_duplicate
    _reject_duplicate_names(file_infos)
    return file_infos, policies


def _reject_duplicate_names(file_infos: list[FileInfo]) -> None:
    """Refuse two files mapping to one resource name; verdicts and resources are keyed by name alone.

    Runs before anything is created: nothing downstream can disambiguate them, and pairing by list
    position instead would upload one file's bytes to another's storage path.
    """
    name_counts = Counter(file_info.name for file_info in file_infos)
    duplicate_names = sorted(name for name, count in name_counts.items() if count > 1)
    if duplicate_names:
        raise BfabricTransferError(
            "Cannot upload multiple files that map to the same resource name: "
            + ", ".join(duplicate_names)
            + " (name-based pairing cannot disambiguate them)."
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
    rest: UploadRestClient, file_infos: list[FileInfo], policies: dict[str, OnDuplicate], container_id: int
) -> tuple[list[FileInfo], list[FileSkip]]:
    # An "upload" policy is a decision, not a question, so those files are left out of the request
    # entirely -- and when every file carries it, no duplicate check is made at all.
    to_check = [fi for fi in file_infos if policies[fi.name] != "upload"]
    if not to_check:
        return file_infos, []
    # Drop any verdict for a name we did not ask about: its file either has an "upload" policy (the
    # decision is already made) or is not ours at all, and either way there is no policy to judge it
    # against. The 'unaccounted' guard below still catches the opposite -- a checked file with no verdict.
    checked_names = {file_info.name for file_info in to_check}
    results = [r for r in rest.check_duplicates(container_id, to_check) if r.filename in checked_names]
    # Guard against a name-normalization mismatch silently dropping a file: every checked file must
    # get a verdict, otherwise a file the server didn't recognise would be miscounted as skipped and
    # never uploaded (silent data loss reported as success).
    verdict_names = {r.filename for r in results}
    unaccounted = sorted(fi.name for fi in to_check if fi.name not in verdict_names)
    if unaccounted:
        raise BfabricTransferError(
            "check-duplicates returned no verdict for: "
            + ", ".join(unaccounted)
            + " (name mismatch between the request and response); refusing to upload to avoid silently "
            'dropping files. Re-run them with on_duplicate="upload" to bypass the duplicate check.'
        )
    # "upload" (new file) and "skip" (exact duplicate already stored) are always actionable; "link"
    # (content-identical bytes already stored elsewhere) only for a file whose own policy asked for
    # it. Any other verdict is one we cannot act on, and folding it into the skipped count would
    # silently fail to register a file the user asked for. Fail loud instead.
    unsupported = sorted(r.filename for r in results if not _is_actionable(r, policies[r.filename]))
    if unsupported:
        # Point at the link policy only when 'link' is actually what we refused; any other verdict is
        # one this client has no handling for at all, so uploading anyway is the only way forward.
        refused_link = any(r.action == "link" for r in results if r.filename in set(unsupported))
        hint = (
            "; these are content-duplicates the server wants registered as links. Re-run them with "
            'on_duplicate="link" to register the links, or on_duplicate="upload" to upload them as '
            "new resources."
            if refused_link
            else "; upload_files cannot act on this verdict. Re-run them with "
            'on_duplicate="upload" to upload them as new resources.'
        )
        raise BfabricTransferError(
            "check-duplicates requested an unsupported action for: " + ", ".join(unsupported) + hint
        )

    # Which files to link rather than transfer. A content-duplicate arrives as action "skip" with an
    # existingResourceId (category exact_duplicate / renamed_duplicate) -- the server does not use
    # action "link" for it -- so linking is driven by a skip verdict that names a resource to link to.
    # An explicit "link" action is honoured too, for a server that does emit it.
    # A skip without an existingResourceId has no link target, so it stays a plain skip.
    link_ids = {
        r.filename: r.resource_id
        for r in results
        if policies[r.filename] == "link" and r.action in ("skip", "link") and r.resource_id is not None
    }
    # A target whose bytes may not exist is unlinkable; those files stay selected but lose their link
    # id, so they are transferred as ordinary uploads instead of being dropped.
    linkable_ids = _select_linkable_targets(link_ids, results)

    # An explicit "link" verdict with no id is unusable: we can neither link nor safely fall back to
    # uploading (the server already told us not to), so fail loud rather than silently drop the file.
    unusable = sorted(r.filename for r in results if r.action == "link" and r.resource_id is None)
    if unusable:
        raise BfabricTransferError(
            "check-duplicates returned a 'link' verdict without an existingResourceId for: "
            + ", ".join(unusable)
            + '; cannot register a link without it. Re-run them with on_duplicate="upload" to upload '
            "them as new resources."
        )

    upload_names = {r.filename for r in results if r.action == "upload"}
    to_upload = [
        replace(fi, link_from_resource_id=linkable_ids[fi.name]) if fi.name in linkable_ids else fi
        for fi in file_infos
        if policies[fi.name] == "upload" or fi.name in upload_names or fi.name in link_ids
    ]
    # Whatever is left over was skipped. Every one of those was checked (an "upload" policy always
    # selects), so each has a verdict to report the duplicate it lost out to.
    selected = {file_info.name for file_info in to_upload}
    verdicts = {r.filename: r for r in results}
    skips = [
        FileSkip(
            filename=fi.name,
            category=verdicts[fi.name].category,
            existing_resource_id=verdicts[fi.name].resource_id,
        )
        for fi in file_infos
        if fi.name not in selected
    ]
    return to_upload, skips


def _is_actionable(result: DuplicateResult, policy: OnDuplicate) -> bool:
    """Whether this client can act on ``result`` for a file uploaded under ``policy``."""
    if result.action in ("upload", "skip"):
        return True
    return result.action == "link" and policy == "link"


_MAX_LOGGED_DROPPED = 5


def _describe_dropped(dropped: list[str], link_ids: dict[str, int], statuses: dict[int, str]) -> str:
    """Name the first few dropped targets and their status, counting the rest.

    Truncated because a single bundle can carry thousands of files, and the per-file detail is a
    diagnostic aid -- the count is the part that always matters.
    """
    shown = ", ".join(
        f"{name} -> resource {link_ids[name]} {statuses.get(link_ids[name], 'not found')}"
        for name in dropped[:_MAX_LOGGED_DROPPED]
    )
    remaining = len(dropped) - _MAX_LOGGED_DROPPED
    return f"{shown} (and {remaining} more)" if remaining > 0 else shown


def _select_linkable_targets(link_ids: dict[str, int], results: list[DuplicateResult]) -> dict[str, int]:
    """Keep the link targets the server reported as ``linkable``.

    ``check-duplicates`` already knows the matched resource's status, so its ``linkable`` verdict is
    the authority: only a resource whose bytes provably exist may be reused as ``linkFromResourceId``.
    A target reported unlinkable -- ``pending`` (nothing conclusive happened yet) or ``failed`` --
    loses its link id and is transferred as an ordinary upload instead, so a retry after a failed
    transfer no longer fails until B-Fabric's orphan cleanup runs.

    A response that does not report ``linkable`` for a target is an error, not a fallback: guessing
    would risk registering a resource with no bytes behind it.
    """
    if not link_ids:
        return link_ids
    verdicts = {r.filename: r.linkable for r in results if r.filename in link_ids}
    unreported = sorted(name for name in link_ids if verdicts.get(name) is None)
    if unreported:
        raise BfabricTransferError(
            "check-duplicates did not report 'linkable' for: "
            + ", ".join(unreported)
            + "; cannot tell whether the matched resource has bytes to link to. This needs a "
            "B-Fabric that reports linkable on /upload/check-duplicates."
        )
    keep = {name: rid for name, rid in link_ids.items() if verdicts[name]}
    dropped = sorted(set(link_ids) - set(keep))
    if dropped:
        statuses = {link_ids[name]: _reported_status(results, name) for name in dropped}
        logger.info(
            "{} file(s) will be uploaded rather than linked: the server reported them unlinkable. {}",
            len(dropped),
            _describe_dropped(dropped, link_ids, statuses),
        )
    return keep


def _reported_status(results: list[DuplicateResult], filename: str) -> str:
    """The status ``check-duplicates`` reported for ``filename``'s match, for logging."""
    for r in results:
        if r.filename == filename:
            return (r.resource_status or "unlinkable").lower()
    return "unlinkable"


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
    return Workunit(result[0], bfabric_instance=client.config.base_url).id


def _create_upload_job(client: Bfabric, workunit_id: int) -> int:
    """Create the ``UPLOAD`` tracking job parented to ``workunit_id`` and return its id.

    The job starts at status ``NEW``; the tus server's own hooks move it to ``DONE``/``FAILED`` once
    the transfer runs, so nothing here mutates its status afterwards.
    """
    result = client.save(
        "job",
        {"action": "UPLOAD", "status": "NEW", "parentclassname": "Workunit", "parentid": workunit_id},
    )
    return Job(result[0], bfabric_instance=client.config.base_url).id


def _pair_resources_to_files(resources: list[CreatedResource], to_upload: list[FileInfo]) -> dict[str, CreatedResource]:
    # Pair each file to its resource by NAME, not list position: create-resources is not guaranteed
    # to preserve request order, and index-pairing would upload one file's bytes to another's path.
    # Name-pairing needs unique names, which _reject_duplicate_names has already established.
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
    adopted: Mapping[str, ResumeEntry],
    workunit_id: int,
    container_id: int,
    job_id: int | None = None,
    on_progress: FileProgressCallback | None,
    on_file_done: FileDoneCallback | None = None,
    on_url: FileUrlCallback | None = None,
    resume_cache: ResumeCache | None = None,
    application_id: int | None = None,
) -> tuple[list[FileUpload], list[FileFailure]]:
    """Transfer each file over tus, recording per-file success/failure.

    A :class:`~bfabric.transfer.TransferError` is recorded and the run continues; any other exception
    propagates so a genuine bug is not silently logged as a flaky upload. ``on_file_done`` fires once
    per file either way, so a caller-side progress counter still reaches the total when files fail.

    A file resumes only from the URL of an entry that was actually ``adopted`` -- the adoption
    decision and the resume have to agree, or the bytes land on the remembered resource while the
    summary names the freshly created one. A URL that turns out to be stale costs one retry from
    byte 0 rather than a failure.
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
        file_url = _make_resume_url_callback(
            on_url,
            file_info,
            resume_cache,
            workunit_id=workunit_id,
            resource=resource,
            container_id=container_id,
            application_id=application_id,
            job_id=job_id,
        )
        try:
            _transfer_one(
                sink,
                file_info,
                creds,
                file_progress,
                file_url,
                resume_cache,
                _resume_url_for(adopted.get(file_info.name), file_info.name, token_result.tus_endpoint),
            )
        except TransferError as error:
            logger.warning("Upload failed for {}: {}", file_info.name, error)
            failures.append(FileFailure(filename=file_info.name, resource_id=resource.id, error=str(error)))
            if on_file_done is not None:
                on_file_done(file_info.name, False)
            continue
        if resume_cache is not None:
            # The bytes are stored; a kept URL would only resume an upload that is already complete.
            resume_cache.discard(md5=file_info.md5, path=str(file_info.path))
        uploads.append(_as_file_upload(file_info.name, resource))
        if on_file_done is not None:
            on_file_done(file_info.name, True)
    return uploads, failures


def _transfer_one(
    sink: TransferSinkTus,
    file_info: FileInfo,
    creds: Credentials,
    on_progress: Callable[[int, int], None] | None,
    on_url: Callable[[str], None] | None,
    resume_cache: ResumeCache | None,
    resume_url: str | None,
) -> None:
    """Send one file, resuming from ``resume_url`` when the caller supplied one.

    A saved URL the server no longer knows about (tusd expired it, or it was never created) fails the
    ``HEAD`` the mover issues; that is not a transport problem, so it costs one restart from byte 0
    rather than a recorded failure. A failure without a resume URL is genuine and propagates.
    """
    try:
        _ = send_to_sink(sink, file_info.path, creds, on_progress=on_progress, on_url=on_url, resume_url=resume_url)
    except TransferError:
        if resume_url is None:
            raise
        logger.info("Resume URL for {} is no longer usable; restarting the upload.", file_info.name)
        assert resume_cache is not None
        resume_cache.discard(md5=file_info.md5, path=str(file_info.path))
        _ = send_to_sink(sink, file_info.path, creds, on_progress=on_progress, on_url=on_url, resume_url=None)


def _resume_url_for(entry: ResumeEntry | None, filename: str, tus_endpoint: str) -> str | None:
    """The adopted URL to continue from, once it is known which endpoint the bytes will go to.

    The same-origin check lives here rather than in the adoption lookup because the tus endpoint is
    only minted after the workunit to adopt has been chosen; a cross-origin URL costs a fresh upload.
    """
    if entry is None:
        return None
    if not same_origin(entry.url, tus_endpoint):
        logger.info("Saved URL for {} is cross-origin with {}; starting afresh.", filename, tus_endpoint)
        return None
    return entry.url


def _make_resume_url_callback(
    on_url: FileUrlCallback | None,
    file_info: FileInfo,
    resume_cache: ResumeCache | None,
    *,
    workunit_id: int,
    resource: CreatedResource,
    container_id: int,
    application_id: int | None,
    job_id: int | None,
) -> Callable[[str], None] | None:
    """The mover's ``(url)`` callback: saves the URL to the cache and forwards it to ``on_url``.

    Saving here rather than after the transfer is the point -- the URL is worth keeping precisely for
    a file whose transfer then fails, and this fires as soon as the URL exists. The workunit and
    resource are stored with it because the URL's tus metadata names them and cannot be repointed:
    continuing this upload means continuing into these same records.
    """
    forward = _make_file_url(on_url, file_info.name)
    if resume_cache is None:
        return forward

    def _report(url: str) -> None:
        resume_cache.store(
            md5=file_info.md5,
            path=str(file_info.path),
            url=url,
            workunit_id=workunit_id,
            resource_id=resource.id,
            container_id=container_id,
            application_id=application_id,
            storage_path=resource.storage_path,
            job_id=job_id,
        )
        if forward is not None:
            forward(url)

    return _report


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


def _make_file_url(on_url: FileUrlCallback | None, filename: str) -> Callable[[str], None] | None:
    """Adapt the mover's ``(url)`` callback to the caller's ``(filename, url)``.

    The mover transfers one file per call and so reports a bare URL; a caller collecting URLs across
    a batch needs to know which file each belongs to.
    """
    if on_url is None:
        return None

    def _report(url: str) -> None:
        on_url(filename, url)

    return _report
