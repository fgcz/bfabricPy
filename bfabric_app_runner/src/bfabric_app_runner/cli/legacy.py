from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import ClassVar

import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict

from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.dispatch.generic import write_chunks_file
from bfabric_app_runner.legacy.shim import UPLOAD_MANIFEST_ENV, materialize_shim_dir
from bfabric_app_runner.specs.inputs.legacy_wrapper_yaml_spec import LegacyWrapperYamlSpec
from bfabric_app_runner.specs.inputs_spec import InputsSpec
from bfabric_app_runner.specs.outputs_spec import CopyResourceSpec, OutputsSpec, SpecType

DEFAULT_CONFIG_FILENAME = "config.yaml"

CHUNK_NAME = "work"
"""Name of the single chunk directory a legacy dispatch creates, relative to the work directory."""

UPLOAD_MANIFEST_FILENAME = "legacy_uploads.txt"
"""File in the chunk directory where the upload shim records the paths a legacy app uploaded."""


class _LegacyApplicationSection(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    output: list[str]


class _LegacyConfig(BaseModel):
    """The one part of the legacy YAML that app-runner reads back; the rest is for the app itself."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    application: _LegacyApplicationSection


def cmd_legacy_dispatch(
    workunit_definition_path: Path,
    work_dir: Path,
    *,
    executable: str,
    output_filename: str | None = None,
    config_filename: str = DEFAULT_CONFIG_FILENAME,
) -> None:
    """Dispatch a legacy app into a single chunk holding just its wrapper-creator YAML.

    Intended as an app's ``dispatch`` command, which appends the workunit definition and work
    directory. A legacy app fetches its own input resources from the scp URLs inside the YAML, so
    nothing else is staged; the chunk's ``inputs.yml`` has exactly one entry.

    :param workunit_definition_path: The workunit definition to read the workunit id from.
    :param work_dir: Directory to dispatch into; the chunk is its ``work`` subdirectory.
    :param executable: The legacy app, recorded as the YAML's ``job_configuration.executable``.
    :param output_filename: Name for the app's output inside the chunk directory; ``None`` uses
        ``output-WU<workunit id>.zip``. Set it for an app whose output is not a zip.
    :param config_filename: Name to write the legacy YAML under.
    """
    definition = WorkunitDefinition.from_yaml(workunit_definition_path)
    if definition.registration is None:
        raise ValueError(f"{workunit_definition_path} has no registration section")
    workunit_id = definition.registration.workunit_id

    # Resolved because the app reads output_path out of the YAML after its own `cd`, so a relative
    # path would send the output somewhere neither the app nor output registration expects.
    chunk_dir = (work_dir / CHUNK_NAME).resolve()
    chunk_dir.mkdir(parents=True, exist_ok=True)
    spec = LegacyWrapperYamlSpec(
        filename=config_filename,
        workunit_id=workunit_id,
        output_path=str(chunk_dir / (output_filename or f"output-WU{workunit_id}.zip")),
        executable=executable,
    )
    InputsSpec.write_yaml([spec], chunk_dir / "inputs.yml")
    # Relative, as ChunksFile documents and Runner.infer_from_directory produces.
    write_chunks_file(work_dir, [Path(CHUNK_NAME)])
    logger.info("Dispatched workunit {} to a single chunk at {}", workunit_id, chunk_dir)


def cmd_legacy_run(executable: str, chunk_dir: Path, *, config_filename: str = DEFAULT_CONFIG_FILENAME) -> None:
    """Run a legacy app against the wrapper-creator YAML in a chunk directory.

    Intended as an app's ``process`` command, which appends the chunk directory. The legacy
    state-writing commands are shadowed by no-ops on ``PATH`` for the duration of the run, and
    ``bfabric_upload_resource.py`` records its file instead of uploading it.

    Once the app succeeds, writes the chunk's ``outputs.yml`` from its declared output and those
    recorded uploads, since a legacy app deposits its files where the YAML told it to but cannot
    declare them for registration. Doing that here rather than in a ``collect`` command keeps a
    legacy app spec to the same two commands a modern app uses.

    :param executable: The legacy app, shell-split; it receives the YAML path as its last argument.
    :param chunk_dir: The chunk directory holding the legacy YAML; ``outputs.yml`` is written here.
    :param config_filename: Name of the legacy YAML inside ``chunk_dir``.
    """
    config_path = _config_path(chunk_dir, config_filename)
    # Checked up front: a remote destination is only detectable from the YAML, and finding out after
    # the app has run would throw away hours of work for something knowable in advance.
    _reject_remote_outputs(_read_config(config_path).application.output)

    manifest = chunk_dir / UPLOAD_MANIFEST_FILENAME
    # A retry of the process step must not inherit the previous run's uploads.
    manifest.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="app-runner-legacy-shims-") as shim_dir:
        env = os.environ.copy()
        # An empty PATH element means the current directory, so fall back to a real default.
        env["PATH"] = os.pathsep.join([str(materialize_shim_dir(Path(shim_dir))), env.get("PATH") or os.defpath])
        env[UPLOAD_MANIFEST_ENV] = str(manifest)
        command = [*shlex.split(executable), str(config_path)]
        logger.info("Running legacy app: {}", shlex.join(command))
        _ = subprocess.run(command, check=True, env=env)
    _write_outputs_spec(chunk_dir, config_path)


def _write_outputs_spec(chunk_dir: Path, config_path: Path) -> None:
    """Declare a legacy app's output and recorded uploads in the chunk's ``outputs.yml``."""
    declared = _read_config(config_path).application.output
    _reject_remote_outputs(declared)
    produced, missing = _partition_declared_outputs(declared)
    uploaded = _uploaded_paths(chunk_dir)
    if missing and not uploaded:
        raise FileNotFoundError(f"The app did not produce its declared output {missing[0]}")
    for path in missing:
        # A few legacy apps only ever upload extra resources, and their scp of the main output is
        # what would have failed the process step, so a missing one here is not on its own an error.
        logger.warning("The app did not write its declared output {}, registering only its uploads", path)

    # An app is free to upload its declared output as well; that is one resource, not a name clash.
    # Keyed on the resolved path, since a declared output and an upload can spell the same file
    # differently, but declared with the path as given so the spec stays readable.
    by_target: dict[Path, Path] = {}
    for path in [*produced, *(_require_file(path) for path in uploaded)]:
        _ = by_target.setdefault(path.resolve(), path)
    copy_specs = [_copy_spec(path) for path in by_target.values()]
    _check_no_duplicate_names(copy_specs)
    specs: list[SpecType] = list(copy_specs)
    outputs_yaml = chunk_dir / "outputs.yml"
    OutputsSpec.write_yaml(specs, outputs_yaml)
    logger.info("Declared {} output(s) in {}", len(specs), outputs_yaml)


def _config_path(chunk_dir: Path, config_filename: str) -> Path:
    config_path = chunk_dir / config_filename
    if not config_path.is_file():
        raise FileNotFoundError(f"No legacy configuration at {config_path}")
    return config_path


def _read_config(config_path: Path) -> _LegacyConfig:
    return _LegacyConfig.model_validate(yaml.safe_load(config_path.read_text()))


def _reject_remote_outputs(outputs: list[str]) -> None:
    """Rejects a ``host:path`` destination, which app-runner cannot register as a local file."""
    for output in outputs:
        if ":" in output:
            msg = (
                f"Cannot register the remote output {output!r}: app-runner registers a local file, so the "
                f"input spec's output_path has to point inside the chunk directory."
            )
            raise ValueError(msg)


def _partition_declared_outputs(outputs: list[str]) -> tuple[list[Path], list[Path]]:
    """Splits ``application.output`` into the paths the app wrote and the ones it did not."""
    produced: list[Path] = []
    missing: list[Path] = []
    for output in outputs:
        path = Path(output)
        (produced if path.is_file() else missing).append(path)
    return produced, missing


def _uploaded_paths(chunk_dir: Path) -> list[Path]:
    """Paths the upload shim recorded, in upload order, dropping repeats of the same path.

    A repeated path is an app uploading the same file twice, which the real command tolerated; two
    *different* paths sharing a basename is a genuine conflict and is left to the duplicate check.
    """
    manifest = chunk_dir / UPLOAD_MANIFEST_FILENAME
    if not manifest.is_file():
        return []
    lines = [line.strip() for line in manifest.read_text().splitlines() if line.strip()]
    return [Path(line) for line in dict.fromkeys(lines)]


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"An uploaded file recorded by the app is gone: {path}")
    return path


def _copy_spec(local_path: Path) -> CopyResourceSpec:
    return CopyResourceSpec(local_path=local_path, store_entry_path=Path(local_path.name))


def _check_no_duplicate_names(specs: list[CopyResourceSpec]) -> None:
    """B-Fabric allows a resource name only once per workunit, so catch a clash before uploading."""
    counts = Counter(spec.store_entry_path.name for spec in specs)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"Multiple legacy outputs share a resource name: {', '.join(duplicates)}")
