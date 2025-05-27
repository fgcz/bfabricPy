import cyclopts
import shlex
import subprocess
from loguru import logger
from pathlib import Path
from bfabric import Bfabric
from bfabric.entities import ExternalJob, Workunit
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.simple_submitter.app_runner_wrapper_template import AppRunnerWrapperTemplate
from bfabric_app_runner.simple_submitter.slurm_job_template import SlurmJobTemplate

app = cyclopts.App()


@app.command()
def wrapper_creator(j: int) -> None:
    """Wrapper creator for simple_submitter."""
    logger.info("Wrapper creator called with job ID:", j)


@app.command()
@use_client
def submitter(j: int, *, client: Bfabric) -> None:
    """Submitter implementation for simple_submitter."""
    # Find the workunit to process
    external_job = ExternalJob.find(id=j, client=client)
    workunit = external_job.workunit
    if workunit is None:
        raise RuntimeError(f"External job {j} does not belong to a workunit (or it was deleted).")

    _submit_workunit(workunit=workunit)


def _submit_workunit(workunit: Workunit) -> None:
    """Submit a workunit to the bfabric app runner."""
    logger.info(f"Submitting workunit {workunit.id}.")

    # Create the wrapped script
    app_runner_wrapper_template_params = AppRunnerWrapperTemplate.Params.extract_workunit(workunit)
    app_runner_wrapper_template = AppRunnerWrapperTemplate(
        params=app_runner_wrapper_template_params, path=AppRunnerWrapperTemplate.default_path()
    )
    wrapped_script = app_runner_wrapper_template.render_string()

    # Create the slurm executable
    slurm_job_template_params = SlurmJobTemplate.Params.extract_workunit(workunit)
    slurm_job_template = SlurmJobTemplate(
        params=slurm_job_template_params, wrapped_script=wrapped_script, path=SlurmJobTemplate.default_path()
    )
    slurm_script = slurm_job_template.render_string()

    # Write this slurm script to the appropriate location
    slurm_script_path = _get_slurm_script_path(workunit_id=workunit.id)
    slurm_script_path.parent.mkdir(exist_ok=True)
    slurm_script_path.write_text(slurm_script)

    # Submit the slurm script and be done.
    cmd = ["sbatch", str(slurm_script_path)]
    logger.info(f"Running slurm submit: {shlex.join(cmd)}")
    subprocess.run(cmd, check=True)


def _get_slurm_script_path(workunit_id: int) -> Path:
    return Path("~/slurmx/").expanduser() / f"workunitid-{workunit_id}.slurm.bash"


if __name__ == "__main__":
    app()
