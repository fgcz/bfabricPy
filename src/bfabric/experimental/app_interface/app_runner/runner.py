from __future__ import annotations

import subprocess
from pathlib import Path
from venv import logger

import yaml
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.experimental.app_interface.app_runner._spec import AppSpec
from bfabric.experimental.app_interface.input_preparation import prepare_folder
from bfabric.experimental.app_interface.output_registration import register_outputs
from bfabric.experimental.app_interface.workunit.definition import WorkunitDefinition


class Runner:
    def __init__(self, spec: AppSpec, client: Bfabric, ssh_user: str | None = None) -> None:
        self._app_spec = spec
        self._client = client
        self._ssh_user = ssh_user

    def run_dispatch(self, workunit_ref: int | Path, work_dir: Path) -> None:
        subprocess.run([*self._app_spec.commands.dispatch.to_shell(), str(workunit_ref), str(work_dir)], check=True)

    def run_prepare_input(self, chunk_dir: Path) -> None:
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yml", target_folder=chunk_dir, client=self._client, ssh_user=self._ssh_user
        )

    def run_collect(self, workunit_ref: int | Path, chunk_dir: Path) -> None:
        subprocess.run([*self._app_spec.commands.collect.to_shell(), str(workunit_ref), str(chunk_dir)], check=True)

    def run_process(self, chunk_dir: Path) -> None:
        subprocess.run([*self._app_spec.commands.process.to_shell(), str(chunk_dir)], check=True)

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
    # TODO future: the workunit definition must be loaded from bfabric exactly once! this is quite inefficient right now
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
    if not read_only:
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "processing"})

    runner = Runner(spec=app_spec, client=client, ssh_user=ssh_user)
    if dispatch_active:
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)
    chunks_file = ChunksFile.model_validate(yaml.safe_load((work_dir / "chunks.yml").read_text()))
    for chunk in chunks_file.chunks:
        logger.info(f"Processing chunk {chunk}")
        runner.run_prepare_input(chunk_dir=chunk)
        runner.run_process(chunk_dir=chunk)
        runner.run_collect(workunit_ref=workunit_ref, chunk_dir=chunk)
        if not read_only:
            runner.run_register_outputs(
                chunk_dir=chunk, workunit_ref=workunit_ref, reuse_default_resource=app_spec.reuse_default_resource
            )

    if not read_only:
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "available"})
