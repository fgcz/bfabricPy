from typing import Literal, Annotated

import cyclopts
import shlex
import subprocess
from loguru import logger
from pathlib import Path
from bfabric import Bfabric
from bfabric.entities import ExternalJob, Workunit
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.bfabric_integration.wrapper.wrap_app_yaml_template import WrapAppYamlTemplate
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_params import evaluate_slurm_parameters
from bfabric_app_runner.bfabric_integration.submitter.slurm_job_template import SlurmJobTemplate

app = cyclopts.App()


JobIdParam = Annotated[int, cyclopts.Parameter(name="-j", help="The externaljob ID to process.")]


@app.command()
def wrapper_creator(j: JobIdParam) -> None:
    """Wrapper creator for simple_submitter."""
    logger.info("Wrapper creator called with job ID:", j)


@app.command()
@use_client
def submitter(
    config_path: Path,
    j: JobIdParam,
    *,
    entity_type: Literal["externaljob", "workunit"] = "externaljob",
    client: Bfabric,
) -> None:
    """Submitter implementation for simple_submitter."""
    if entity_type == "externaljob":
        # Find the workunit to process
        external_job = ExternalJob.find(id=j, client=client)
        workunit = external_job.workunit
        if workunit is None:
            raise RuntimeError(f"External job {j} does not belong to a workunit (or it was deleted).")
    else:
        workunit = Workunit.find(id=j, client=client)

    _submit_workunit(workunit=workunit, config_path=config_path)


def _submit_workunit(workunit: Workunit, config_path: Path) -> None:
    """Submit a workunit to the bfabric app runner."""
    logger.info(f"Submitting workunit {workunit.id}.")
    slurm_params = evaluate_slurm_parameters(config_yaml_path=config_path, workunit=workunit)

    # Create the wrapped script
    wrap_app_yaml_template_params = WrapAppYamlTemplate.Params.extract_workunit(
        workunit, scratch_root=slurm_params.scratch_root
    )
    wrap_app_yaml_template = WrapAppYamlTemplate(
        params=wrap_app_yaml_template_params, path=WrapAppYamlTemplate.default_path()
    )
    wrapped_script = wrap_app_yaml_template.render_string()

    # Create the slurm executable
    slurm_job_template = SlurmJobTemplate(
        params=slurm_params,
        workunit_id=workunit.id,
        wrapped_script=wrapped_script,
        path=SlurmJobTemplate.default_path(),
    )
    slurm_script = slurm_job_template.render_string()

    # Ensure log dir exists
    if "--output" in slurm_params.sbatch_params:
        log_dir = Path(slurm_params.sbatch_params["--output"]).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Write this slurm script to the appropriate location
    slurm_script_path = slurm_params.job_script
    slurm_script_path.parent.mkdir(exist_ok=True)
    slurm_script_path.write_text(slurm_script)

    # Submit the slurm script and be done.
    cmd = ["sbatch", str(slurm_script_path)]
    logger.info(f"Running slurm submit: {shlex.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    app()
