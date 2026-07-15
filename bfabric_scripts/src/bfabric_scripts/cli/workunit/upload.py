from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, final

import cyclopts
from loguru import logger
from pydantic import BaseModel, model_validator
from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

from bfabric import Bfabric
from bfabric.operations.workunit import UploadFilesParams, upload_files
from bfabric.utils.cli_integration import use_client

if TYPE_CHECKING:
    from collections.abc import Iterator


@cyclopts.Parameter(name="*")
class UploadParams(BaseModel):
    # ``files`` is the sole positional argument. A positional ``list`` is greedy in cyclopts, so every
    # other field is forced keyword-only (explicit ``--name``); otherwise ``files`` would swallow the
    # container/application tokens (``upload FILES CONTAINER-ID APPLICATION-ID`` never bound the ids).
    files: list[Path]
    """Files and/or directories to upload; directories are expanded recursively."""
    container_id: Annotated[int | None, cyclopts.Parameter(name="--container-id")] = None
    """The container (order/project) to create the workunit in. Required unless ``--workunit-id`` is given."""
    application_id: Annotated[int | None, cyclopts.Parameter(name="--application-id")] = None
    """The application the workunit belongs to. Required unless ``--workunit-id`` is given."""
    workunit_id: Annotated[int | None, cyclopts.Parameter(name="--workunit-id")] = None
    """Upload into this existing workunit instead of creating a new one. Mutually exclusive with ``--workunit-name``."""
    workunit_name: Annotated[str | None, cyclopts.Parameter(name="--workunit-name")] = None
    """Name for the created workunit (``None`` → "File upload"); mutually exclusive with ``--workunit-id``."""
    force: bool = False
    """Skip the duplicate check and upload every file."""
    track_job: bool = False
    """Create a ``UPLOAD`` job tracking the upload; the tus server flips it to DONE/FAILED."""
    progress: bool = True
    """Show a live upload progress bar. Pass ``--no-progress`` to disable; it is also
    auto-disabled when stderr is not an interactive terminal."""

    @model_validator(mode="after")
    def _validate_target(self) -> UploadParams:
        if self.workunit_id is not None:
            if self.workunit_name is not None:
                raise ValueError("--workunit-name and --workunit-id are mutually exclusive.")
        else:
            missing = [
                flag
                for flag, value in (("--container-id", self.container_id), ("--application-id", self.application_id))
                if value is None
            ]
            if missing:
                raise ValueError(f"{' and '.join(missing)} required unless --workunit-id is given.")
        return self


@use_client
def cmd_workunit_upload(params: UploadParams, *, client: Bfabric) -> None:
    """Upload files to a B-Fabric workunit over tus (resumable).

    Creates a new workunit, or uploads into an existing one with ``--workunit-id``. Requires an
    OAuth-backed client with the ``tus`` scope; authenticate with
    ``bfabric-cli auth login --scope "api:read api:write openid profile email groups tus"``.
    """
    with _upload_progress(enabled=_progress_enabled(requested=params.progress)) as reporter:
        summary = upload_files(
            client=client,
            files=params.files,
            params=UploadFilesParams(
                container_id=params.container_id,
                application_id=params.application_id,
                workunit_id=params.workunit_id,
                workunit_name=params.workunit_name,
                force=params.force,
                track_job=params.track_job,
            ),
            on_progress=reporter.on_progress if reporter else None,
            on_start=reporter.on_start if reporter else None,
            on_file_done=reporter.on_file_done if reporter else None,
        )

    if summary.workunit_id is None:
        logger.info(f"Nothing to upload ({summary.skipped} file(s) skipped as duplicates).")
        return

    job_note = f" (tracking job {summary.job_id})" if summary.job_id is not None else ""
    logger.success(
        f"Workunit {summary.workunit_id}{job_note}: uploaded {summary.uploaded} file(s), "
        f"skipped {summary.skipped}, failed {summary.failed}."
    )
    for failure in summary.failures:
        logger.error(f"  Failed: {failure.filename}: {failure.error}")


def _progress_enabled(*, requested: bool) -> bool:
    """Show the live bar only when asked for and stderr is a terminal (never when piped/redirected)."""
    return requested and sys.stderr.isatty()


@final
class _UploadProgressReporter:
    """Drives the live upload display: an overall ``N/X`` bar, a per-file bar, and a persistent list.

    Files upload sequentially, so one per-file bar is shown at a time -- created when its first chunk
    is reported and removed once it finishes. Each completed file also prints a persistent ✓/✗ line
    above the live region (via ``live.console.print``) so the user keeps a scrollback history of what
    has been uploaded while still seeing where they are in the whole batch.
    """

    def __init__(self, *, live: Live, overall: Progress, current: Progress) -> None:
        self._live = live
        self._overall = overall
        self._current = current
        self._overall_task: TaskID | None = None
        self._file_tasks: dict[str, TaskID] = {}
        self._total_files = 0
        self._done = 0

    def on_start(self, total_files: int, _total_bytes: int) -> None:
        # _total_bytes is part of the on_start contract but unused: the overall bar is file-count only
        # (a byte-% / ETA bar would consume it -- see the CLI plan). Underscore marks it intentional.
        self._total_files = total_files
        self._overall_task = self._overall.add_task("Overall", total=total_files)

    def on_progress(self, filename: str, bytes_done: int, total: int) -> None:
        task_id = self._file_tasks.get(filename)
        if task_id is None:
            task_id = self._current.add_task(filename, total=total)
            self._file_tasks[filename] = task_id
        self._current.update(task_id, completed=bytes_done, total=total)

    def on_file_done(self, filename: str, success: bool) -> None:
        task_id = self._file_tasks.pop(filename, None)
        if task_id is not None:
            self._current.remove_task(task_id)
        self._done += 1
        if self._overall_task is not None:
            self._overall.update(self._overall_task, completed=self._done)
        mark = "[green]✓[/]" if success else "[red]✗[/]"
        self._live.console.print(f"{mark} [{self._done}/{self._total_files}] {filename}")


@contextmanager
def _upload_progress(*, enabled: bool) -> Iterator[_UploadProgressReporter | None]:
    """Yield a live-backed :class:`_UploadProgressReporter`, or ``None`` when disabled.

    Rendered on stderr next to the log output. Both progress bars live in a single ``Live`` so they
    stay pinned together; ``transient`` clears them on exit, leaving the persistent per-file list and
    the final summary line.
    """
    if not enabled:
        yield None
        return
    console = Console(file=sys.stderr)
    overall = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    current = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    )
    with Live(Group(overall, current), console=console, transient=True) as live:
        yield _UploadProgressReporter(live=live, overall=overall, current=current)
