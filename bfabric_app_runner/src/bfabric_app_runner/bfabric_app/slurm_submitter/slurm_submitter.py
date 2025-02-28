from __future__ import annotations

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
        self, target_path: Path, wrapper_data: WorkunitWrapperData, log_resource_id: int | None
    ) -> None:
        slurm_config = self.evaluate_config(wrapper_data)
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

    def _get_force_storage_flag(self, slurm_config: SlurmConfig) -> str:
        return (
            ""
            if not slurm_config.submitter_config.config.force_storage
            else f"--force-storage {str(slurm_config.submitter_config.config.force_storage)}"
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
