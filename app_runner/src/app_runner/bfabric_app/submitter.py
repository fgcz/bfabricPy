import argparse
import base64
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from app_runner.specs.submitters_spec import SubmittersSpec
from app_runner.submitter.config.slurm_config_template import SlurmConfigTemplate
from app_runner.submitter.config.slurm_workunit_params import SlurmWorkunitParams
from app_runner.submitter.slurm_submitter import SlurmSubmitter
from bfabric import Bfabric
from bfabric.entities import ExternalJob, Executable
from bfabric_scripts.cli.base import use_client

if TYPE_CHECKING:
    from app_runner.specs.submitter_ref import SubmitterRef


class Submitter:
    def __init__(self, client: Bfabric, external_job: ExternalJob, submitters_spec: SubmittersSpec) -> None:
        self._client = client
        self._external_job = external_job
        self._workunit = external_job.workunit
        self._submitters_spec = submitters_spec

    def get_workunit_wrapper_data(self) -> WorkunitWrapperData:
        # find the executable
        # TODO why not available
        # executables = Executable.find_by({"workunitid": self._workunit.id,
        #     "context": "WORKUNIT"}, client=self._client)
        executables = Executable.find_by({"workunitid": self._workunit.id}, client=self._client)
        executables = {key: value for key, value in executables.items() if value["context"] == "WORKUNIT"}
        if len(executables) != 1:
            msg = f"Expected exactly one WORKUNIT executable, found executables: {sorted(executables.keys())}"
            raise ValueError(msg)
        executable = list(executables.values())[0]

        # read the wrapper data
        yaml_data = base64.b64decode(executable["base64"].encode()).decode()
        return WorkunitWrapperData.model_validate(yaml.safe_load(yaml_data))

    def run(self) -> None:
        workunit_wrapper_data = self.get_workunit_wrapper_data()
        submitter_ref: SubmitterRef = workunit_wrapper_data.app_version.submitter
        submitter_name = submitter_ref.name
        submitter_spec = self._submitters_spec.submitters.get(submitter_name)
        if submitter_spec is None:
            raise ValueError(f"Submitter '{submitter_name}' not found in submitters spec.")
        if submitter_spec.type != "slurm":
            raise ValueError(f"Submitter '{submitter_name}' is not of type 'slurm'.")
        workunit_config = SlurmWorkunitParams.model_validate(
            workunit_wrapper_data.workunit_definition.execution.raw_parameters
        )
        slurm_config_template = SlurmConfigTemplate(
            submitter_config=submitter_spec,
            app_version=workunit_wrapper_data.app_version,
            workunit_config=workunit_config,
        )
        submitter = SlurmSubmitter(slurm_config_template)
        submitter.submit(workunit_wrapper_data=workunit_wrapper_data)


@use_client
def app(*, client: Bfabric) -> None:
    """CLI interface for slurm submitter."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--submitters-yml", type=Path)
    parser.add_argument("-j", type=int)
    args = parser.parse_args()
    external_job = ExternalJob.find(id=args.j, client=client)
    submitters_spec = SubmittersSpec.model_validate(yaml.safe_load(args.submitters_yml.read_text()))
    submitter = Submitter(client=client, external_job=external_job, submitters_spec=submitters_spec)
    submitter.run()


if __name__ == "__main__":
    app()
