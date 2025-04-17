from __future__ import annotations

import argparse
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from bfabric_app_runner.app_runner.resolve_app import resolve_app
from bfabric_app_runner.bfabric_app.slurm_submitter.config.slurm_config_template import SlurmConfigTemplate
from bfabric_app_runner.bfabric_app.slurm_submitter.config.slurm_workunit_params import SlurmWorkunitParams
from bfabric_app_runner.bfabric_app.slurm_submitter.slurm_submitter import SlurmSubmitter
from bfabric_app_runner.specs.app.app_spec import AppSpecTemplate
from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from bfabric_app_runner.specs.config_interpolation import Variables, VariablesApp, VariablesWorkunit
from bfabric_app_runner.specs.submitters_spec import SubmittersSpecTemplate, SubmitterSlurmSpec
from loguru import logger
from pydantic import BaseModel

from bfabric.entities import ExternalJob, Workunit, Executable
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.submitter_ref import SubmitterRef


class Submitter:
    def __init__(
        self, client: Bfabric, external_job: ExternalJob, submitters_spec_template: SubmittersSpecTemplate
    ) -> None:
        self._client = client
        self._external_job = external_job
        self._submitters_spec_template = submitters_spec_template

    @cached_property
    def _workunit_id(self) -> int:
        # TODO this should be lazy and only return the id
        #  (do we add workunit_id or implement something like a lazy getter)
        return self._external_job.workunit.id

    def get_workunit_wrapper_data(self) -> WorkunitWrapperData:
        return get_data(workunit=self._external_job.workunit)

    def get_submitter_spec(self, workunit_wrapper_data: WorkunitWrapperData) -> SubmitterSlurmSpec:
        """Retrieves the submitter spec for the workunit."""
        # Get information on the submitter
        submitter_ref: SubmitterRef = workunit_wrapper_data.app_version.submitter
        submitter_name = submitter_ref.name

        # Construct the interpolation variables
        variables = Variables(
            app=VariablesApp(
                id=workunit_wrapper_data.workunit_definition.registration.application_id,
                name=workunit_wrapper_data.workunit_definition.registration.application_name,
                version=workunit_wrapper_data.app_version.version,
            ),
            workunit=VariablesWorkunit(id=workunit_wrapper_data.workunit_definition.registration.workunit_id),
        )

        # Evaluate the submitters spec
        submitters_spec = self._submitters_spec_template.evaluate(variables=variables)
        submitter_spec = submitters_spec.submitters.get(submitter_name)

        if submitter_spec is None:
            msg = f"Submitter '{submitter_name}' not found in submitters spec."
            raise ValueError(msg)
        if not isinstance(submitter_spec, SubmitterSlurmSpec):
            msg = f"Submitter '{submitter_name}' is not a Slurm submitter."
            raise ValueError(msg)

        return submitter_spec

    def run(self) -> None:
        workunit_wrapper_data = self.get_workunit_wrapper_data()
        workunit_config = SlurmWorkunitParams.model_validate(
            workunit_wrapper_data.workunit_definition.execution.raw_parameters
        )
        submitter_spec = self.get_submitter_spec(workunit_wrapper_data=workunit_wrapper_data)
        slurm_config_template = SlurmConfigTemplate(
            submitter_config=submitter_spec,
            app_version=workunit_wrapper_data.app_version,
            workunit_config=workunit_config,
        )
        submitter = SlurmSubmitter(slurm_config_template)
        submitter.submit(workunit_wrapper_data=workunit_wrapper_data, client=self._client)


class WorkunitWrapperData(BaseModel):
    workunit_definition: WorkunitDefinition
    app_version: AppVersion
    app_runner_version: str


def get_application_yaml_path(executable: Executable) -> Path:
    """Returns the path to the application YAML file."""
    # TODO for now this is hardcoded, but a better solution might be considered later
    program_str = executable["program"]
    if "fgcz_slurm_app_runner_compat.bash" in program_str:
        return Path(program_str.split()[-1])
    else:
        return Path(program_str)


def get_data(workunit: Workunit) -> WorkunitWrapperData:
    """Returns the data to be written to WORKUNIT context executable."""
    # TODO this can certainly be cleaned up further, it's an interim refactoring state
    workunit_definition = WorkunitDefinition.from_workunit(workunit=workunit)
    path = get_application_yaml_path(workunit.application.executable)
    logger.info("Reading app spec from: {}", path)
    app_spec_template = AppSpecTemplate.model_validate(yaml.safe_load(path.read_text()))
    app_spec = app_spec_template.evaluate(
        app_id=workunit_definition.registration.application_id,
        app_name=workunit_definition.registration.application_name,
    )
    app_version = resolve_app(versions=app_spec, workunit_definition=workunit_definition)
    app_runner_version = app_spec.bfabric.app_runner
    return WorkunitWrapperData(
        workunit_definition=workunit_definition, app_version=app_version, app_runner_version=app_runner_version
    )


@use_client
@logger.catch(reraise=True)
def app(*, client: Bfabric) -> None:
    """CLI interface for slurm submitter."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--submitters-yml", type=Path)
    parser.add_argument("-j", type=int)
    args = parser.parse_args()
    external_job = ExternalJob.find(id=args.j, client=client)
    submitters_spec_template = SubmittersSpecTemplate.model_validate(yaml.safe_load(args.submitters_yml.read_text()))
    submitter = Submitter(client=client, external_job=external_job, submitters_spec_template=submitters_spec_template)
    submitter.run()


if __name__ == "__main__":
    app()
