from __future__ import annotations

import os
import shlex
import subprocess
from typing import TYPE_CHECKING

from loguru import logger

from bfabric_app_runner.bfabric_app.slurm_job_template import SlurmJobTemplate
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit

if TYPE_CHECKING:
    from bfabric import Bfabric
    from pathlib import Path
    from bfabric_app_runner.bfabric_app.slurm_submitter.config.slurm_config import SlurmConfig
    from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
    from bfabric_app_runner.bfabric_app.slurm_submitter.config.slurm_config_template import SlurmConfigTemplate


class SlurmSubmitter:
    def __init__(self, config_template: SlurmConfigTemplate) -> None:
        self._config_template = config_template

    def submit(self, workunit_wrapper_data: WorkunitWrapperData, client: Bfabric) -> None:
        slurm_config = self.evaluate_config(workunit_wrapper_data)

        # Determine the script path
        workunit_id = workunit_wrapper_data.workunit_definition.registration.workunit_id
        script_path = slurm_config.submitter_config.config.local_script_dir / f"workunitid-{workunit_id}_run.bash"

        # Generate the script
        log_resource_id = self._create_log_resource(config=slurm_config, workunit_id=workunit_id, client=client)
        self.generate_script(
            target_path=script_path,
            slurm_config=slurm_config,
            wrapper_data=workunit_wrapper_data,
            log_resource_id=log_resource_id,
        )

        # Submit the script
        sbatch_bin = slurm_config.submitter_config.config.slurm_root / "bin" / "sbatch"
        env = os.environ | {"SLURMROOT": slurm_config.submitter_config.config.slurm_root}
        logger.info("Script written to {}", script_path)
        cmd = [str(sbatch_bin), str(script_path)]
        logger.info("Running {}", shlex.join(cmd))
        subprocess.run(cmd, env=env, check=True)

    def evaluate_config(self, workunit_wrapper_data: WorkunitWrapperData) -> SlurmConfig:
        app = VariablesApp(
            id=workunit_wrapper_data.workunit_definition.registration.application_id,
            name=workunit_wrapper_data.workunit_definition.registration.application_name,
            version=workunit_wrapper_data.app_version.version,
        )
        workunit = VariablesWorkunit(id=workunit_wrapper_data.workunit_definition.registration.workunit_id)
        return self._config_template.evaluate(app=app, workunit=workunit)

    def _create_log_resource(self, config: SlurmConfig, workunit_id: int, client: Bfabric) -> int | None:
        """Creates the log resource and returns its id, or if no log storage ID is provided, returns None."""
        if config.submitter_config.config.log_storage_id is None:
            logger.info("No log storage ID provided, skipping log resource creation")
            return None

        return client.save(
            "resource",
            {
                "name": f"Developer Log WU{workunit_id}",
                "relativepath": config.submitter_config.config.log_storage_filename,
                "storageid": config.submitter_config.config.log_storage_id,
                "workunitid": workunit_id,
                "status": "pending",
            },
        )[0]["id"]

    def generate_script(
        self,
        target_path: Path,
        slurm_config: SlurmConfig,
        wrapper_data: WorkunitWrapperData,
        log_resource_id: int | None,
    ) -> None:
        main_command = self._get_main_command(
            slurm_config=slurm_config, app_runner_version=wrapper_data.app_runner_version
        )
        slurm_job_template = SlurmJobTemplate.for_params(
            app_version=wrapper_data.app_version,
            workunit_definition=wrapper_data.workunit_definition,
            working_directory=slurm_config.submitter_config.config.worker_scratch_dir,
            logging_resource_id=log_resource_id,
            command=main_command,
            sbatch_params=slurm_config.sbatch_params,
        )
        with target_path.open("w") as target_file:
            slurm_job_template.render(target_file=target_file)

    def _get_force_storage_flag(self, slurm_config: SlurmConfig) -> list[str]:
        return (
            []
            if not slurm_config.submitter_config.config.force_storage
            else ["--force-storage", str(slurm_config.submitter_config.config.force_storage)]
        )

    def _get_main_command(self, slurm_config: SlurmConfig, app_runner_version: str) -> list[str]:
        spec = f"@{app_runner_version}" if "git" in app_runner_version else f"=={app_runner_version}"
        force_storage_flags = self._get_force_storage_flag(slurm_config)
        return [
            "uv",
            "run",
            "-p",
            "3.13",
            "--with",
            f"bfabric_app_runner{spec}",
            "bfabric-app-runner",
            "app",
            "run",
            "--app-spec",
            "app_version.yml",
            "--workunit-ref",
            "workunit_definition.yml",
            *force_storage_flags,
            "--work-dir",
            "$(pwd)",
        ]
