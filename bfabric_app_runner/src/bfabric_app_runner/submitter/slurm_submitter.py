from __future__ import annotations

import os
import shlex
import subprocess
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.submitters_spec import SubmitterSlurmSpec
    from bfabric_app_runner.submitter.config.slurm_config import SlurmConfig
    from bfabric_app_runner.submitter.config.slurm_config_template import SlurmConfigTemplate
    from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData

_MAIN_BASH_TEMPLATE = """
set -euxo pipefail
hostname
id
mkdir -p "{working_directory}"
cd "{working_directory}"

set +x
tee app_version.yml <<YAML
{app_version_yml}
YAML

tee workunit_definition.yml <<YAML
{workunit_definition_yml}
YAML

trap 'code=$?; [ $code -ne 0 ] && bfabric-cli api save workunit {workunit_id} status failed; exit $code' EXIT

set -x
{{
{app_runner_command} \\
  app run --app-spec app_version.yml --workunit-ref workunit_definition.yml {force_storage_flags} --work-dir "$(pwd)"
}} 2>&1 | ts '[%Y-%m-%d %H:%M:%S]'
"""  # noqa: E501


class SlurmSubmitter:
    def __init__(self, config_template: SlurmConfigTemplate) -> None:
        self._config_template = config_template

    def _compose_script_header(self, concrete_params: dict[str, str]) -> str:
        return "\n".join(["#!/bin/bash"] + [f"#SBATCH {key}={value}" for key, value in concrete_params.items()])

    def _compose_script(self, main_command: str, slurm_config: SlurmConfig) -> str:
        script_header = self._compose_script_header(slurm_config.sbatch_params)
        return f"{script_header}\n\n{main_command}"

    def _get_main_command(
        self, workunit_wrapper_data: WorkunitWrapperData, working_directory: str, submitter_config: SubmitterSlurmSpec
    ) -> str:
        app_version_yml = yaml.safe_dump(workunit_wrapper_data.app_version.model_dump(mode="json"))
        workunit_definition_yml = yaml.safe_dump(workunit_wrapper_data.workunit_definition.model_dump(mode="json"))
        app_runner_version = workunit_wrapper_data.app_runner_version
        force_storage_flags = (
            ""
            if not submitter_config.config.force_storage
            else f"--force-storage {str(submitter_config.config.force_storage)}"
        )
        render_args = dict(
            app_version_yml=app_version_yml,
            workunit_definition_yml=workunit_definition_yml,
            app_runner_command=self._get_app_runner_command(version=app_runner_version),
            working_directory=working_directory,
            force_storage_flags=force_storage_flags,
            workunit_id=workunit_wrapper_data.workunit_definition.registration.workunit_id,
        )
        logger.info("Render args: {}", render_args)
        return _MAIN_BASH_TEMPLATE.format(**render_args)

    @staticmethod
    def _get_app_runner_command(version: str) -> str:
        spec = f"@{version}" if "git" in version else f"=={version}"
        return f'uv run -p 3.13 --with "bfabric_app_runner{spec}" bfabric-app-runner'

    def _add_link_to_logs(
        self, client: Bfabric, workunit_wrapper_data: WorkunitWrapperData, submitter_config: SubmitterSlurmSpec
    ) -> None:
        if submitter_config.config.log_viewer_url:
            workunit_id = workunit_wrapper_data.workunit_definition.registration.workunit_id
            obj = {
                "name": f"WU{workunit_id} Logs",
                "parentclassname": "workunit",
                "parentid": workunit_id,
                "url": submitter_config.config.log_viewer_url,
            }
            client.save("link", obj)

    def evaluate_config(self, workunit_wrapper_data: WorkunitWrapperData) -> SlurmConfig:
        app = VariablesApp(
            id=workunit_wrapper_data.workunit_definition.registration.application_id,
            name=workunit_wrapper_data.workunit_definition.registration.application_name,
            version=workunit_wrapper_data.app_version.version,
        )
        workunit = VariablesWorkunit(id=workunit_wrapper_data.workunit_definition.registration.workunit_id)
        return self._config_template.evaluate(app=app, workunit=workunit)

    def submit(self, workunit_wrapper_data: WorkunitWrapperData) -> None:
        # Evaluate the config
        slurm_config = self.evaluate_config(workunit_wrapper_data=workunit_wrapper_data)
        logger.info("Slurm Config: {}", slurm_config)

        # Determine the script path
        workunit_id = workunit_wrapper_data.workunit_definition.registration.workunit_id
        script_path = slurm_config.submitter_config.config.local_script_dir / f"workunitid-{workunit_id}_run.bash"

        # Determine the working directory.
        working_directory = slurm_config.get_scratch_dir()

        # Generate the script
        main_command = self._get_main_command(
            workunit_wrapper_data=workunit_wrapper_data,
            working_directory=working_directory,
            submitter_config=slurm_config.submitter_config,
        )
        script = self._compose_script(main_command=main_command, slurm_config=slurm_config)
        script_path.write_text(script)
        script_path.chmod(0o755)

        # Add link to logs
        self._add_link_to_logs(
            client=workunit_wrapper_data.client,
            workunit_wrapper_data=workunit_wrapper_data,
            submitter_config=slurm_config.submitter_config,
        )

        # Execute sbatch
        sbatch_bin = slurm_config.submitter_config.config.slurm_root / "bin" / "sbatch"
        env = os.environ | {"SLURMROOT": slurm_config.submitter_config.config.slurm_root}
        logger.info("Script written to {}", script_path)
        cmd = [str(sbatch_bin), str(script_path)]
        logger.info("Running {}", shlex.join(cmd))
        subprocess.run(cmd, env=env, check=True)
