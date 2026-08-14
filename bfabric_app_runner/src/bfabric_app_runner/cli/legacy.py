from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
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

UPLOAD_MANIFEST_FILENAME = "legacy_uploads.txt"
"""File in the chunk directory where the upload shim records the paths a legacy app uploaded."""


class _LegacyApplicationSection(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    output: list[str]


class _LegacyConfig(BaseModel):
    """The one part of the legacy YAML that ``collect`` needs; the rest is for the app itself."""

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

    :param executable: The legacy app, recorded as the YAML's ``job_configuration.executable``.
    :param output_filename: Name for the app's output inside the chunk directory; ``None`` uses
        ``output-WU<workunit id>.zip``. Set it for an app whose output is not a zip.
    :param config_filename: Name to write the legacy YAML under.
    """
    definition = WorkunitDefinition.from_yaml(workunit_definition_path)
    if definition.registration is None:
        raise ValueError(f"{workunit_definition_path} has no registration section")
    workunit_id = definition.registration.workunit_id

    chunk_dir = work_dir / "work"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    spec = LegacyWrapperYamlSpec(
        filename=config_filename,
        workunit_id=workunit_id,
        output_path=str(chunk_dir / (output_filename or f"output-WU{workunit_id}.zip")),
        executable=executable,
    )
    InputsSpec.write_yaml([spec], chunk_dir / "inputs.yml")
    write_chunks_file(work_dir, [chunk_dir])
    logger.info("Dispatched workunit {} to a single chunk at {}", workunit_id, chunk_dir)


def cmd_legacy_run(executable: str, chunk_dir: Path, *, config_filename: str = DEFAULT_CONFIG_FILENAME) -> None:
    """Run a legacy app against the wrapper-creator YAML in a chunk directory.

    Intended as an app's ``process`` command, which appends the chunk directory. The legacy
    state-writing commands are shadowed by no-ops on ``PATH`` for the duration of the run, and
    ``bfabric_upload_resource.py`` records its file for ``legacy collect`` instead of uploading it.

    :param executable: The legacy app, shell-split; it receives the YAML path as its last argument.
    :param chunk_dir: The chunk directory holding the legacy YAML.
    :param config_filename: Name of the legacy YAML inside ``chunk_dir``.
    """
    config_path = _config_path(chunk_dir, config_filename)
    with tempfile.TemporaryDirectory(prefix="app-runner-legacy-shims-") as shim_dir:
        env = os.environ.copy()
        env["PATH"] = f"{materialize_shim_dir(Path(shim_dir))}:{env.get('PATH', '')}"
        env[UPLOAD_MANIFEST_ENV] = str(chunk_dir / UPLOAD_MANIFEST_FILENAME)
        command = [*shlex.split(executable), str(config_path)]
        logger.info("Running legacy app: {}", shlex.join(command))
        _ = subprocess.run(command, check=True, env=env)


def cmd_legacy_collect(chunk_dir: Path, *, config_filename: str = DEFAULT_CONFIG_FILENAME) -> None:
    """Write a chunk's ``outputs.yml`` from a legacy app's declared output and recorded uploads.

    Intended as an app's ``collect`` command, since a legacy app deposits its files where the YAML
    told it to but cannot declare them for registration.

    :param chunk_dir: The chunk directory holding the legacy YAML; ``outputs.yml`` is written here.
    :param config_filename: Name of the legacy YAML inside ``chunk_dir``.
    """
    config = _LegacyConfig.model_validate(yaml.safe_load(_config_path(chunk_dir, config_filename).read_text()))
    uploaded = _uploaded_paths(chunk_dir)
    produced, missing = _partition_declared_outputs(config.application.output)
    if missing and not uploaded:
        raise FileNotFoundError(f"The app did not produce its declared output {missing[0]}")
    for path in missing:
        # A few legacy apps only ever upload extra resources, and their scp of the main output is
        # what would have failed the process step, so a missing one here is not on its own an error.
        logger.warning("The app did not write its declared output {}, registering only its uploads", path)

    specs: list[SpecType] = [_copy_spec(path) for path in produced]
    specs += [_copy_spec(_require_file(path)) for path in uploaded]
    _check_no_duplicate_names(specs)
    outputs_yaml = chunk_dir / "outputs.yml"
    OutputsSpec.write_yaml(specs, outputs_yaml)
    logger.info("Declared {} output(s) in {}", len(specs), outputs_yaml)


def _config_path(chunk_dir: Path, config_filename: str) -> Path:
    config_path = chunk_dir / config_filename
    if not config_path.is_file():
        raise FileNotFoundError(f"No legacy configuration at {config_path}")
    return config_path


def _partition_declared_outputs(outputs: list[str]) -> tuple[list[Path], list[Path]]:
    """Splits ``application.output`` into the paths the app wrote and the ones it did not."""
    produced: list[Path] = []
    missing: list[Path] = []
    for output in outputs:
        if ":" in output:
            msg = (
                f"Cannot register the remote output {output!r}: app-runner registers a local file, so the "
                f"input spec's output_path has to point inside the chunk directory."
            )
            raise ValueError(msg)
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


def _check_no_duplicate_names(specs: list[SpecType]) -> None:
    """B-Fabric allows a resource name only once per workunit, so catch a clash before uploading."""
    names = [spec.store_entry_path.name for spec in specs if isinstance(spec, CopyResourceSpec)]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Multiple legacy outputs share a resource name: {', '.join(duplicates)}")
