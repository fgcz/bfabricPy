from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bfabric_app_runner.commands.execute import execute_command
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder
from bfabric_app_runner.output_registration import register_outputs
from loguru import logger
from pydantic import BaseModel

from bfabric.experimental.workunit_definition import WorkunitDefinition

if TYPE_CHECKING:
    from bfabric_app_runner.specs.app.app_version import AppVersion
    from bfabric import Bfabric


class Runner:
    """Executes the individual lifecycle steps (dispatch, inputs, process, collect) of a single app version."""

    def __init__(self, spec: AppVersion, client: Bfabric, ssh_user: str | None = None) -> None:
        self._app_version = spec
        self._client = client
        self._ssh_user = ssh_user

    def run_dispatch(self, workunit_ref: int | Path, work_dir: Path) -> None:
        """Runs the app's dispatch command, which splits the workunit into chunk directories under ``work_dir``."""
        logger.info(f"Calling dispatch for workunit {workunit_ref} in {work_dir}")
        execute_command(self._app_version.commands.dispatch, str(workunit_ref), str(work_dir))

    def run_inputs(self, chunk_dir: Path) -> None:
        """Stages the input files declared in the chunk's ``inputs.yml`` into the chunk directory."""
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yml",
            target_folder=chunk_dir,
            client=self._client,
            ssh_user=self._ssh_user,
            filter=None,
        )

    def run_process(self, chunk_dir: Path) -> None:
        """Runs the app's process command on a single prepared chunk directory."""
        logger.info(f"Calling process for chunk directory {chunk_dir}")
        execute_command(self._app_version.commands.process, str(chunk_dir))

    def run_collect(self, workunit_ref: int | Path, chunk_dir: Path) -> None:
        """Runs the app's collect command for a chunk, or does nothing if the app has no collect step."""
        if self._app_version.commands.collect is not None:
            logger.info(f"Calling collect for workunit {workunit_ref} in {chunk_dir}")
            execute_command(self._app_version.commands.collect, str(workunit_ref), str(chunk_dir))
        else:
            logger.info("App does not have a collect step.")


class ChunksFile(BaseModel):
    """Lists the chunk subdirectories that make up a workunit's work directory (``chunks.yml``)."""

    # TODO move to better location
    chunks: list[Path]
    """Chunk directories relative to the work directory; each is processed independently."""

    @classmethod
    def infer_from_directory(cls, work_dir: Path) -> ChunksFile:
        """Infer chunks by scanning for subdirectories containing inputs.yml.

        :param work_dir: The work directory to scan
        :return: ChunksFile with discovered chunks
        :raises ValueError: If no chunks are found
        """
        # Scan for subdirectories containing inputs.yml (non-recursive, 1 level deep)
        work_dir = work_dir.resolve()
        chunk_dirs = [p.parent.relative_to(work_dir) for p in work_dir.glob("*/inputs.yml")]

        # Fail if no chunks found
        if not chunk_dirs:
            msg = f"No chunks found in {work_dir}. Expected subdirectories containing 'inputs.yml' files."
            raise ValueError(msg)

        # Sort alphabetically for consistent ordering
        chunk_dirs.sort()
        logger.info(f"Auto-discovered {len(chunk_dirs)} chunk(s): {[str(d) for d in chunk_dirs]}")
        return ChunksFile(chunks=chunk_dirs)

    @classmethod
    def read(cls, work_dir: Path) -> ChunksFile:
        """Reads the chunks.yml file from the specified work directory.

        If chunks.yml is missing, automatically discovers chunks by scanning for
        subdirectories containing inputs.yml and writes the result to chunks.yml.

        :param work_dir: The work directory containing chunks.yml or chunk subdirectories
        :return: ChunksFile with chunk paths
        """
        chunks_file = work_dir / "chunks.yml"
        try:
            return ChunksFile.model_validate(yaml.safe_load(chunks_file.read_text()))
        except FileNotFoundError:
            logger.info(f"chunks.yml not found in {work_dir}, auto-discovering chunks...")
            chunks = cls.infer_from_directory(work_dir)
            # Write discovered chunks to file for traceability
            with chunks_file.open("w") as f:
                yaml.safe_dump(chunks.model_dump(mode="json"), f)
            logger.info(f"Created chunks.yml with {len(chunks.chunks)} chunk(s)")
            return chunks


def run_app(
    app_spec: AppVersion,
    workunit_ref: int | Path,
    work_dir: Path,
    client: Bfabric,
    force_storage: Path | None,
    ssh_user: str | None = None,
    read_only: bool = False,
    dispatch_active: bool = True,
) -> None:
    """Executes all steps of the provided app: dispatch, then inputs/process/collect for every chunk.

    Unless ``read_only`` is set, the workunit status is set to ``processing`` before the run and to
    ``available`` once all chunks have been processed.

    :param app_spec: Resolved app version whose commands and settings drive execution.
    :param workunit_ref: Workunit to run, either a B-Fabric workunit ID or a path to a workunit definition YAML.
    :param work_dir: Directory in which inputs, chunks, and outputs are staged.
    :param client: B-Fabric client used to read the workunit and register outputs.
    :param force_storage: Overrides the storage used for output registration; ``None`` uses the default storage.
    :param ssh_user: SSH user for staging inputs and copying outputs; ``None`` uses the current user.
    :param read_only: When True, skips all B-Fabric mutations (workunit status updates and output registration).
    :param dispatch_active: When True, runs the dispatch step; set False to reuse an existing chunk layout.
    """
    # TODO would it be possible, to reuse the individual steps commands so there is certainly only one definition?
    work_dir = work_dir.resolve()
    workunit_ref = workunit_ref.resolve() if isinstance(workunit_ref, Path) else workunit_ref

    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(
        workunit=workunit_ref, client=client, cache_file=workunit_definition_file
    )
    if not read_only:
        # Set the workunit status to processing
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "processing"})

    runner = Runner(spec=app_spec, client=client, ssh_user=ssh_user)
    if dispatch_active:
        runner.run_dispatch(workunit_ref=workunit_definition_file, work_dir=work_dir)
    chunks_file = ChunksFile.read(work_dir=work_dir)
    for chunk in chunks_file.chunks:
        logger.info(f"Processing chunk {chunk}")
        runner.run_inputs(chunk_dir=chunk)
        runner.run_process(chunk_dir=chunk)
        runner.run_collect(workunit_ref=workunit_definition_file, chunk_dir=chunk)
        if not read_only:
            register_outputs(
                outputs_yaml=chunk / "outputs.yml",
                workunit_definition=workunit_definition,
                client=client,
                ssh_user=ssh_user,
                reuse_default_resource=app_spec.reuse_default_resource,
                force_storage=force_storage,
            )

    if not read_only:
        # Set the workunit status to available
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "available"})
