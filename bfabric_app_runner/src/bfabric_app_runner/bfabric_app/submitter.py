import argparse
import base64
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from bfabric import Bfabric
from bfabric.entities import ExternalJob, Executable
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from bfabric_app_runner.specs.config_interpolation import Variables, VariablesApp, VariablesWorkunit
from bfabric_app_runner.specs.submitters_spec import SubmittersSpecTemplate, SubmitterSlurmSpec
from bfabric_app_runner.submitter.config.slurm_config_template import SlurmConfigTemplate
from bfabric_app_runner.submitter.config.slurm_workunit_params import SlurmWorkunitParams
from bfabric_app_runner.submitter.slurm_submitter import SlurmSubmitter

if TYPE_CHECKING:
    from bfabric_app_runner.specs.submitter_ref import SubmitterRef


class Submitter:
    def __init__(
        self, client: Bfabric, external_job: ExternalJob, submitters_spec_template: SubmittersSpecTemplate
    ) -> None:
        self._client = client
        self._external_job = external_job
        self._workunit = external_job.workunit
        self._submitters_spec_template = submitters_spec_template

    def get_workunit_wrapper_data(self) -> WorkunitWrapperData:
        # Find the executable
        executables = Executable.find_by({"workunitid": self._workunit.id}, client=self._client)
        executables = {key: value for key, value in executables.items() if value["context"] == "WORKUNIT"}
        if len(executables) != 1:
            msg = f"Expected exactly one WORKUNIT executable, found executables: {sorted(executables.keys())}"
            raise ValueError(msg)
        executable = list(executables.values())[0]

        # Read the wrapper data
        yaml_data = base64.b64decode(executable["base64"].encode()).decode()
        return WorkunitWrapperData.model_validate(yaml.safe_load(yaml_data))

    def get_submitter_spec(self, workunit_wrapper_data: WorkunitWrapperData) -> SubmitterSlurmSpec:
        """Retrieves the submitter spec for the workunit."""
        # Get information on the submitter
        submitter_ref: SubmitterRef = workunit_wrapper_data.app_version.submitter
        submitter_name = submitter_ref.name

        # Construct the interpolation variables
        variables = Variables(
            app=VariablesApp(
                id=self._workunit.application.id,
                name=self._workunit.application["name"],
                version=workunit_wrapper_data.app_version.version,
            ),
            workunit=VariablesWorkunit(id=self._workunit.id),
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
        submitter.submit(workunit_wrapper_data=workunit_wrapper_data)
        submitter.create_monitor_links(workunit_wrapper_data=workunit_wrapper_data, client=self._client)


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
