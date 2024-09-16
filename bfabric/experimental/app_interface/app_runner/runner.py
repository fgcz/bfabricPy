from __future__ import annotations
import shlex
import subprocess
from pathlib import Path

from bfabric import Bfabric
from bfabric.experimental.app_interface.app_runner._spec import AppSpec
from bfabric.experimental.app_interface.input_preparation import prepare_folder
from bfabric.experimental.app_interface.output_registration import register_outputs


class Runner:
    def __init__(self, spec: AppSpec, client: Bfabric, ssh_user: str | None = None) -> None:
        self._app_spec = spec
        self._client = client
        self._ssh_user = ssh_user

    def run_dispatch(self, workunit_ref: int | Path, work_dir: Path) -> None:
        subprocess.run(
            f"{self._app_spec.dispatch} {shlex.quote(str(workunit_ref))} {shlex.quote(str(work_dir))}",
            shell=True,
            check=True,
        )

    def run_prepare_input(self, chunk_dir: Path) -> None:
        prepare_folder(
            inputs_yaml=chunk_dir / "inputs.yaml", target_folder=chunk_dir, client=self._client, ssh_user=self._ssh_user
        )

    def run_process(self, chunk_dir: Path) -> None:
        subprocess.run(f"{self._app_spec.process} {shlex.quote(str(chunk_dir))}", shell=True, check=True)

    def run_register_outputs(self, chunk_dir: Path, workunit_id: int) -> None:
        register_outputs(
            outputs_yaml=chunk_dir / "outputs.yaml",
            workunit_id=workunit_id,
            client=self._client,
            ssh_user=self._ssh_user,
        )
