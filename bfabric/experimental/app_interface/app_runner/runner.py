from __future__ import annotations
import shlex
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
        subprocess.run(
            f"{self._app_spec.commands.dispatch} {shlex.quote(str(workunit_ref))} {shlex.quote(str(work_dir))}",
            shell=True,
            check=True,
        )

    def run_prepare_input(self, chunk_dir: Path) -> None:
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yml", target_folder=chunk_dir, client=self._client, ssh_user=self._ssh_user
        )

    def run_process(self, chunk_dir: Path) -> None:
        subprocess.run(f"{self._app_spec.commands.process} {shlex.quote(str(chunk_dir))}", shell=True, check=True)

    def run_register_outputs(self, chunk_dir: Path, workunit_ref: int | Path) -> None:
        workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=self._client)
        register_outputs(
            outputs_yaml=chunk_dir / "outputs.yml",
            workunit_id=workunit_definition.registration.workunit_id,
            client=self._client,
            ssh_user=self._ssh_user,
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
) -> None:
    runner = Runner(spec=app_spec, client=client, ssh_user=ssh_user)
    runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)
    chunks_file = ChunksFile.model_validate(yaml.safe_load((work_dir / "chunks.yml").read_text()))
    for chunk in chunks_file.chunks:
        logger.info(f"Processing chunk {chunk}")
        runner.run_prepare_input(chunk_dir=chunk)
        runner.run_process(chunk_dir=chunk)
        if not read_only:
            runner.run_register_outputs(chunk_dir=chunk, workunit_ref=workunit_ref)
