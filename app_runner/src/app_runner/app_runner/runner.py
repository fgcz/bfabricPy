from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric
from app_runner.app_runner._spec import AppSpec
from app_runner.input_preparation import prepare_folder
from app_runner.output_registration import register_outputs
from bfabric.experimental.workunit_definition import WorkunitDefinition


class Runner:
    def __init__(self, spec: AppSpec, client: Bfabric, ssh_user: str | None = None) -> None:
        self._app_spec = spec
        self._client = client
        self._ssh_user = ssh_user

    def run_dispatch(self, workunit_ref: int | Path, work_dir: Path) -> None:
        command = [*self._app_spec.commands.dispatch.to_shell(), str(workunit_ref), str(work_dir)]
        logger.info(f"Running dispatch command: {shlex.join(command)}")
        subprocess.run(command, check=True)

    def run_prepare_input(self, chunk_dir: Path) -> None:
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yml", target_folder=chunk_dir, client=self._client, ssh_user=self._ssh_user
        )

    def run_collect(self, workunit_ref: int | Path, chunk_dir: Path) -> None:
        command = [*self._app_spec.commands.collect.to_shell(), str(workunit_ref), str(chunk_dir)]
        logger.info(f"Running collect command: {shlex.join(command)}")
        subprocess.run(command, check=True)

    def run_process(self, chunk_dir: Path) -> None:
        command = [*self._app_spec.commands.process.to_shell(), str(chunk_dir)]
        logger.info(f"Running process command: {shlex.join(command)}")
        subprocess.run(command, check=True)

    def run_register_outputs(self, chunk_dir: Path, workunit_ref: int | Path, reuse_default_resource: bool) -> None:
        workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=self._client)
        register_outputs(
            outputs_yaml=chunk_dir / "outputs.yml",
            workunit_id=workunit_definition.registration.workunit_id,
            client=self._client,
            ssh_user=self._ssh_user,
            reuse_default_resource=reuse_default_resource,
        )


class ChunksFile(BaseModel):
    # TODO move to better location
    chunks: list[Path]


def run_app(
    app_spec: AppSpec,
    workunit_ref: int | Path,
    work_dir: Path,
    client: Bfabric,
    ssh_user: str | None = None,
    read_only: bool = False,
    dispatch_active: bool = True,
) -> None:
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
    chunks_file = ChunksFile.model_validate(yaml.safe_load((work_dir / "chunks.yml").read_text()))
    for chunk in chunks_file.chunks:
        logger.info(f"Processing chunk {chunk}")
        runner.run_prepare_input(chunk_dir=chunk)
        runner.run_process(chunk_dir=chunk)
        runner.run_collect(workunit_ref=workunit_definition_file, chunk_dir=chunk)
        if not read_only:
            runner.run_register_outputs(
                chunk_dir=chunk,
                workunit_ref=workunit_definition_file,
                reuse_default_resource=app_spec.reuse_default_resource,
            )

    if not read_only:
        # Set the workunit status to available
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "available"})
