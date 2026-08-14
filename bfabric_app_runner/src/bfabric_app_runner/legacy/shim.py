from __future__ import annotations

import stat
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path

NOOP_COMMANDS = (
    "bfabric_setResourceStatus_available.py",
    "bfabric_setExternalJobStatus_done.py",
    "bfabric_setWorkunitStatus_processing.py",
    "bfabric_setWorkunitStatus_available.py",
    "bfabric_setWorkunitStatus_failed.py",
    "bfabric_save_workflowstep.py",
)
"""Legacy state-writing commands a legacy app must not run under app-runner.

app-runner sets the workunit status, the resource status and the workflow step itself, and the ids in
the legacy YAML are sentinels, so these calls would at best duplicate work and at worst mark the
wrong entity.
"""

UPLOAD_COMMAND = "bfabric_upload_resource.py"
"""Legacy extra-resource upload, recorded for later registration rather than neutralised.

The real command base64s the file over SOAP, which makes B-Fabric file it on its internal storage
instead of the application's. Noting the path for ``legacy collect`` instead puts those resources on
the same storage as every other app-runner output and keeps the internal repo out of the picture.
"""

SHIMMED_COMMANDS = (*NOOP_COMMANDS, UPLOAD_COMMAND)

UPLOAD_MANIFEST_ENV = "APP_RUNNER_LEGACY_UPLOAD_MANIFEST"
"""Env var by which ``legacy run`` tells the upload shim where to record uploaded paths."""

_NOOP_SCRIPT = """#!/bin/sh
echo "[app-runner legacy shim] ignoring: $(basename "$0") $*" >&2
exit 0
"""

# Records the path instead of copying the file: no legacy app removes its scratch directory before
# exiting, so a copy would only duplicate output that can be arbitrarily large. Mirrors the real
# command's tolerance of a missing file, since callers habitually append `|| { echo failed; }`.
_UPLOAD_SCRIPT = f"""#!/bin/sh
file="$1"
if [ -z "${{{UPLOAD_MANIFEST_ENV}:-}}" ]; then
    echo "[app-runner legacy shim] no upload manifest set, ignoring upload of '$file'" >&2
    exit 0
fi
if [ ! -f "$file" ]; then
    echo "[app-runner legacy shim] no such file, ignoring upload of '$file'" >&2
    exit 0
fi
case "$file" in
    /*) path="$file" ;;
    *) path="$PWD/$file" ;;
esac
printf '%s\\n' "$path" >> "${{{UPLOAD_MANIFEST_ENV}}}" || exit 1
echo "[app-runner legacy shim] recorded '$path' for registration" >&2
exit 0
"""

_EXECUTABLE_BITS = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


def materialize_shim_dir(path: Path) -> Path:
    """Writes an executable shim for every command in :data:`SHIMMED_COMMANDS` into ``path``.

    Generated rather than shipped as package data, since nothing preserves an executable bit through
    a wheel and app-runner itself often runs from an ephemeral ``uv run --with`` environment.
    """
    path.mkdir(parents=True, exist_ok=True)
    for command in SHIMMED_COMMANDS:
        script = path / command
        _ = script.write_text(_UPLOAD_SCRIPT if command == UPLOAD_COMMAND else _NOOP_SCRIPT)
        script.chmod(script.stat().st_mode | _EXECUTABLE_BITS)
    logger.debug("Materialized {} legacy shims in {}", len(SHIMMED_COMMANDS), path)
    return path
