from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder
from bfabric_app_runner.output_registration import register_outputs
from loguru import logger
from pydantic import BaseModel

from bfabric.experimental.workunit_definition import WorkunitDefinition

if TYPE_CHECKING:
    from bfabric_app_runner.specs.app.app_version import AppVersion
    from bfabric import Bfabric


class Runner:
    def __init__(self, spec: AppVersion, client: Bfabric, ssh_user: str | None = None) -> None:
        self._app_version = spec
        self._client = client
        self._ssh_user = ssh_user

    def run_dispatch(self, workunit_ref: int | Path, work_dir: Path) -> None:
        command = [*self._app_version.commands.dispatch.to_shell(), str(workunit_ref), str(work_dir)]
        env = self._app_version.commands.dispatch.to_shell_env(environ=os.environ)
        logger.info(f"Running dispatch command: {shlex.join(command)}")
        logger.debug(f"Split command: {command!r}")
        subprocess.run(command, check=True, env=env)

    def run_prepare_input(self, chunk_dir: Path) -> None:
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yml",
            target_folder=chunk_dir,
            client=self._client,
            ssh_user=self._ssh_user,
            filter=None,
        )

    def run_collect(self, workunit_ref: int | Path, chunk_dir: Path) -> None:
        if self._app_version.commands.collect is not None:
            command = [*self._app_version.commands.collect.to_shell(), str(workunit_ref), str(chunk_dir)]
            env = self._app_version.commands.collect.to_shell_env(environ=os.environ)
            logger.info(f"Running collect command: {shlex.join(command)}")
            logger.debug(f"Split command: {command!r}")
            subprocess.run(command, check=True, env=env)
        else:
            logger.info("App does not have a collect step.")

    def run_process(self, chunk_dir: Path) -> None:
        command = [*self._app_version.commands.process.to_shell(), str(chunk_dir)]
        env = self._app_version.commands.process.to_shell_env(environ=os.environ)
        logger.info(f"Running process command: {shlex.join(command)}")
        logger.debug(f"Split command: {command!r}")
        subprocess.run(command, check=True, env=env)


class ChunksFile(BaseModel):
    # TODO move to better location
    chunks: list[Path]

    @classmethod
    def read(cls, work_dir: Path) -> ChunksFile:
        """Reads the chunks.yml file from the specified work directory."""
        return ChunksFile.model_validate(yaml.safe_load((work_dir / "chunks.yml").read_text()))


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
    """Executes all steps of the provided app."""
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
        runner.run_prepare_input(chunk_dir=chunk)
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
