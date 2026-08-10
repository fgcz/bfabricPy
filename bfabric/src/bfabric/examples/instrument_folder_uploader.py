"""Marker-driven, idempotent uploader for instrument data folders.

Model (see the fleet discussion):

- Each subfolder of a watched directory becomes one B-Fabric workunit.
- A run is uploaded only once its **marker file** appears (operator presses "done", or the
  acquisition software drops it). The marker only ever signals "done" -- it is never written to.
- The folder -> workunit-id memory lives in a **sidecar state file** outside the watched tree
  (``state_dir/<folder>.json``), so later scans reuse the same workunit instead of creating a new
  one. Keeping it out of the run folder is deliberate: ``upload_files`` expands the folder
  recursively, so a state file inside it would be uploaded as a resource, and because its content
  changes after every upload its md5 would change too -- defeating the dedup below and re-uploading
  it on every single scan.
- Re-running is safe and cheap: on the reuse path ``upload_files`` checksums each file and skips the
  ones already stored (md5 dedup), so a folder that gained new files uploads only the new ones into
  the SAME workunit; a folder with nothing new transfers nothing.
- A **new** run, by contrast, uploads unconditionally (``force=True``). B-Fabric's duplicate check is
  container-wide, not per-run, so an unrelated run that happened to produce byte-identical content (a
  calibration file, a blank, an empty spectrum) would otherwise suppress this run's copy -- leaving
  the folder with no workunit of its own and, since there would then be no id to remember, stranded
  on the create path for every future scan. Instrument runs are events, not content: two runs that
  produce identical bytes are still two runs. The operator placing the marker is the deliberate
  assertion that this is a genuine new acquisition, so that is the authority we upload on.
- A recency filter keeps each scan fast and avoids touching long-finished runs.

This is deliberately a thin wrapper: the resumable transfer, dedup, and per-file failure isolation
all live in ``bfabric.operations.workunit.upload_files``. The only things this script owns are
"which folders are done" (marker) and "which workunit each folder maps to" (sidecar state file).

Run it from cron / a systemd timer every few minutes. It is stateless beyond the marker and state
files and safe to run repeatedly (each folder is independent).

The operator's marker sits inside the run folder (that is where the operator is when the run ends)
but is never uploaded: it is passed to ``upload_files`` as ``exclude_names``, which filters by
basename during the folder expansion, so nested files keep their relative resource names.

Configuration lives in one YAML file per machine (``--config``), so a fleet of machines shares this
one script and differs only in its config. The config carries a **service-user OAuth client** (id +
secret, client-credentials grant): ``Bfabric.connect_oauth`` fetches and refreshes that token itself
and caches it on disk, so the machine runs unattended. The scope MUST include ``tus`` (the default
OAuth scope does not) and the extra ``bfabric[transfer]`` must be installed.

Example ``uploader.yml``::

    base_url: https://bfabric.example.com/bfabric
    client_id: svc-instrument-uploader
    client_secret: "s3cr3t..."          # or set BFABRIC_UPLOADER_CLIENT_SECRET in the env
    scope: "api:read api:write openid profile email groups tus"
    machine_id: ms-042
    watch_dir: /data/instrument_out
    state_dir: /var/lib/bfabric-uploader  # folder -> workunit-id memory; MUST be outside watch_dir
    marker_name: .bfabric_upload         # optional; the "run finished" flag operators create
    container_id: 1234
    application_id: 567
    recency_days: 7                      # optional, default 7
    token_cache_path: ~/.cache/bfabric/uploader-token.json   # optional

Usage:
    python -m bfabric.examples.instrument_folder_uploader --config /etc/bfabric/uploader.yml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from loguru import logger
from pydantic import BaseModel, SecretStr, model_validator

from bfabric import Bfabric
from bfabric.operations.workunit import UploadFilesParams, upload_files

DEFAULT_MARKER_NAME = ".bfabric_upload"
"""Default marker filename; override per machine with ``marker_name`` in the config.

Presence = 'run finished, upload me'. Never written to; the workunit id lives in the state file."""

SECRET_ENV_VAR = "BFABRIC_UPLOADER_CLIENT_SECRET"
"""Env override for the client secret, so it need not sit in the config file on disk."""


class UploaderConfig(BaseModel):
    """One machine's uploader configuration, loaded from a YAML file."""

    base_url: str
    """B-Fabric instance URL, e.g. ``https://bfabric.example.com/bfabric``."""
    client_id: str
    """Service-user OAuth client id (client-credentials grant)."""
    client_secret: SecretStr = SecretStr("")
    """Service-user OAuth client secret. Prefer the ``BFABRIC_UPLOADER_CLIENT_SECRET`` env var over
    putting this in the file; the env var, when set, overrides the file value."""
    scope: str = "api:read api:write openid profile email groups tus"
    """OAuth scope. MUST include ``tus`` -- the library default does not, so it is spelled out here."""
    machine_id: str
    """This machine's id; embedded in each workunit name for humans reading B-Fabric."""
    watch_dir: Path
    """Directory whose immediate subfolders are runs."""
    marker_name: str = DEFAULT_MARKER_NAME
    """Filename the operator (or the acquisition software) creates inside a run folder to signal
    "this run is finished, upload it". Its contents are irrelevant and never read -- an empty file
    is the normal case. Override this when a site already has its own done-flag convention."""
    state_dir: Path
    """Where the folder -> workunit-id state files live. MUST be outside ``watch_dir`` (validated):
    a state file inside a run folder would be uploaded as a resource, and its content changes after
    every upload, so its md5 would change too and dedup would re-upload it on every scan."""
    container_id: int
    """Container new workunits are created in."""
    application_id: int
    """Application new workunits belong to."""
    recency_days: int = 7
    """Only upload folders whose newest file was modified within this many days."""
    token_cache_path: Path | None = None
    """Where to cache the OAuth token so it survives restarts (``None`` lets the library choose)."""

    @model_validator(mode="after")
    def _apply_secret_env_and_check_scope(self) -> UploaderConfig:
        env_secret = os.environ.get(SECRET_ENV_VAR)
        if env_secret:
            self.client_secret = SecretStr(env_secret)
        if not self.client_secret.get_secret_value():
            raise ValueError(
                f"No client_secret: set it in the config file or the {SECRET_ENV_VAR} environment variable."
            )
        if "tus" not in self.scope.split():
            raise ValueError("scope must include 'tus' (the upload uses the tus transport).")
        # A marker with a path separator would never be found by the per-folder existence check, so
        # every run would be silently skipped -- fail at load instead of scanning forever finding nothing.
        if not self.marker_name or self.marker_name.strip() != self.marker_name:
            raise ValueError("marker_name must be a non-empty filename without leading/trailing whitespace.")
        if "/" in self.marker_name or self.marker_name in (".", ".."):
            raise ValueError(f"marker_name must be a plain filename, not a path: {self.marker_name!r}")
        return self

    @classmethod
    def load(cls, path: Path) -> UploaderConfig:
        data: object = yaml.safe_load(path.expanduser().read_text()) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Config {path} must be a YAML mapping.")
        cfg = cls.model_validate(data)
        cfg.watch_dir = cfg.watch_dir.expanduser()
        cfg.state_dir = cfg.state_dir.expanduser()
        if cfg.token_cache_path is not None:
            cfg.token_cache_path = cfg.token_cache_path.expanduser()
        # Checked after expanduser (and resolved, so symlinks/.. cannot smuggle state_dir back inside)
        # rather than in the model validator, which sees the raw unexpanded values.
        watch, state = cfg.watch_dir.resolve(), cfg.state_dir.resolve()
        if watch == state or watch in state.parents:
            raise ValueError(
                f"state_dir ({cfg.state_dir}) must not be inside watch_dir ({cfg.watch_dir}): state files "
                "there would be uploaded as resources and re-uploaded on every scan."
            )
        return cfg


@dataclass
class FolderState:
    """A folder's remembered upload state, stored in ``state_dir/<folder>.json``.

    ``workunit_id is None`` means the folder is flagged done but has never been uploaded yet -- this
    scan will create its workunit. A non-None id means reuse that workunit and upload only new files.
    """

    workunit_id: int | None

    @staticmethod
    def path_for(state_dir: Path, folder: Path) -> Path:
        return state_dir / f"{folder.name}.json"

    @classmethod
    def read(cls, path: Path) -> FolderState:
        # A missing state file is the normal first-scan case and means "not yet uploaded". Only a
        # present, well-formed "workunit_id" pins an existing workunit.
        try:
            raw = path.read_text().strip()
        except OSError:
            return cls(workunit_id=None)
        if not raw:
            return cls(workunit_id=None)
        try:
            parsed = cast("object", json.loads(raw))
            data = cast("dict[str, object]", parsed) if isinstance(parsed, dict) else {}
            wid = data.get("workunit_id")
            return cls(workunit_id=int(wid) if wid is not None else None)  # pyright: ignore[reportArgumentType]
        except (json.JSONDecodeError, ValueError, TypeError):
            # A malformed state file is treated as "not uploaded" rather than crashing the whole scan;
            # worst case is one duplicate workunit, which is recoverable, unlike losing the run.
            logger.warning("State file {} is malformed; treating folder as not-yet-uploaded.", path)
            return cls(workunit_id=None)

    def write(self, path: Path, *, workunit_id: int) -> None:
        """Atomically persist ``workunit_id`` (write to a temp file, then rename over the target).

        A bare ``write_text`` truncates first, so a crash or full disk mid-write would leave an empty
        state file -- which :meth:`read` maps to "not yet uploaded", causing the next scan to create a
        DUPLICATE workunit for the folder. ``os.replace`` is atomic within a filesystem, so a reader
        sees either the old id or the new one, never a torn write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp")
        _ = tmp.write_text(json.dumps({"workunit_id": workunit_id}))
        os.replace(tmp, path)


def newest_mtime(folder: Path, *, marker_name: str) -> float:
    """Most recent mtime of any file under ``folder`` (0.0 if it contains no files).

    The marker is excluded: touching it is what *starts* the upload, so counting it would make every
    freshly-marked folder look active regardless of when the run actually finished.
    """
    mtimes = [f.stat().st_mtime for f in folder.rglob("*") if f.is_file() and f.name != marker_name]
    return max(mtimes, default=0.0)


def find_ready_folders(watch_dir: Path, *, recency_days: int, marker_name: str) -> list[Path]:
    """Subfolders that are (a) marked done and (b) recently active.

    A folder without a marker is skipped: it is either mid-acquisition or the operator has not
    pressed 'done' yet. Uploading it would risk capturing a half-written file, which dedup would then
    consider final and never re-check.
    """
    cutoff = time.time() - recency_days * 86400
    ready: list[Path] = []
    for folder in sorted(p for p in watch_dir.iterdir() if p.is_dir()):
        if not (folder / marker_name).exists():
            continue
        if newest_mtime(folder, marker_name=marker_name) < cutoff:
            logger.debug("Skipping {} (no activity in the last {} days).", folder.name, recency_days)
            continue
        ready.append(folder)
    return ready


def upload_folder(client: Bfabric, folder: Path, cfg: UploaderConfig) -> None:
    """Upload one folder as a workunit, creating it or reusing the state file's remembered id.

    The workunit name embeds the machine id purely for humans reading B-Fabric; correctness of the
    'same workunit' reuse comes from the id in the state file, never from the name.
    """
    state_path = FolderState.path_for(cfg.state_dir, folder)
    state = FolderState.read(state_path)
    workunit_name = f"{cfg.machine_id}/{folder.name}"
    is_new_run = state.workunit_id is None

    summary = upload_files(
        client=client,
        files=[folder],
        params=UploadFilesParams(
            # Create path (workunit_id is None) needs container + application; reuse path ignores them.
            container_id=cfg.container_id if is_new_run else None,
            application_id=cfg.application_id if is_new_run else None,
            workunit_id=state.workunit_id,
            workunit_name=workunit_name if is_new_run else None,
            # A new run uploads unconditionally: B-Fabric's duplicate check is container-wide, so an
            # unrelated run that happened to produce identical bytes (a calibration file, a blank)
            # would otherwise suppress this run's copy and leave it with no workunit at all. The
            # operator placing the marker is the assertion that this is a genuine new acquisition.
            # On the reuse path dedup is exactly what we want: skip what this scan already uploaded
            # and send only the new files.
            force=is_new_run,
            track_job=True,  # server-side DONE/FAILED visibility per upload
        ),
        # The operator's marker lives inside the run folder; it is a signal, not data.
        exclude_names={cfg.marker_name},
    )

    if summary.workunit_id is None:
        # Unreachable in practice: force=True on the create path means nothing is ever skipped, so a
        # workunit is always created. Guarded anyway so a future change to that flag cannot silently
        # skip persisting the id -- which would strand the folder on the create path forever.
        logger.warning(
            "{}: no workunit was created ({} file(s) skipped); folder left unrecorded.",
            folder.name,
            summary.skipped,
        )
        return

    # Persist the id so the next scan reuses this workunit. Idempotent: rewriting the same id is a no-op.
    state.write(state_path, workunit_id=summary.workunit_id)
    logger.success(
        "{} -> workunit {}: uploaded {}, skipped {}, failed {}.",
        folder.name,
        summary.workunit_id,
        summary.uploaded,
        summary.skipped,
        summary.failed,
    )
    for failure in summary.failures:
        logger.error("  Failed {}: {}", failure.filename, failure.error)


def connect(cfg: UploaderConfig) -> Bfabric:
    """Connect as the service user via OAuth client-credentials (token auto-refreshed + disk-cached)."""
    return Bfabric.connect_oauth(
        client_id=cfg.client_id,
        client_secret=cfg.client_secret.get_secret_value(),
        base_url=cfg.base_url,
        scope=cfg.scope,
        token_cache_path=cfg.token_cache_path,
    )


def run_scan(cfg: UploaderConfig) -> int:
    """One full scan. Returns the number of folders that hit an unexpected error."""
    client = connect(cfg)
    folders = find_ready_folders(cfg.watch_dir, recency_days=cfg.recency_days, marker_name=cfg.marker_name)
    logger.info("Found {} folder(s) ready to upload under {}.", len(folders), cfg.watch_dir)

    errors = 0
    for folder in folders:
        try:
            upload_folder(client, folder, cfg)
        except Exception:
            # One bad folder must not stop the fleet's scan; log it and move on. The marker and state
            # file are left as-is so the next scan retries it (per-file failures are in the summary).
            logger.exception("Unexpected error uploading {}; will retry next scan.", folder.name)
            errors += 1
    return errors


def main(argv: list[str] | None = None) -> int:
    # Deliberately NOT __doc__: the module docstring is design rationale for whoever reads the
    # source, whereas --help is read by an operator who needs to know what to do. Keep it to the
    # marker convention and the config, and name the marker file explicitly.
    parser = argparse.ArgumentParser(
        description=(
            f"Upload finished instrument run folders to B-Fabric.\n\n"
            f"Scans each immediate subfolder of the configured watch_dir and uploads the ones marked\n"
            f"as finished. A run counts as finished once a marker file exists inside its folder:\n\n"
            f"    <run folder>/{DEFAULT_MARKER_NAME}   (default name; set 'marker_name' to change it)\n\n"
            f"The marker's contents are irrelevant and never read -- an empty file is the normal case:\n\n"
            f"    touch /path/to/run_001/{DEFAULT_MARKER_NAME}\n\n"
            f"Re-running is safe: each folder maps to one workunit (remembered in state_dir), so a\n"
            f"second scan uploads only files that are new and transfers nothing when nothing changed.\n"
            f"Set {SECRET_ENV_VAR} in the environment rather than storing the secret in the config."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _ = parser.add_argument("--config", type=Path, required=True, help="Path to the machine's uploader YAML config.")
    args = parser.parse_args(argv)
    config_path = Path(str(args.config))  # pyright: ignore[reportAny]  # argparse Namespace is untyped

    try:
        cfg = UploaderConfig.load(config_path)
    except (OSError, ValueError) as error:
        logger.error("Could not load config {}: {}", config_path, error)
        return 2

    if not cfg.watch_dir.is_dir():
        logger.error("Watch dir {} does not exist.", cfg.watch_dir)
        return 2

    # Create it up front: a state_dir that is unwritable (wrong owner under cron, read-only mount)
    # would otherwise surface only after a successful upload, losing that workunit id.
    try:
        cfg.state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.error("Cannot create state dir {}: {}", cfg.state_dir, error)
        return 2

    errors = run_scan(cfg)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
