# noqa: TC001, TC002, TC003
import argparse
import base64

import yaml

from app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from bfabric import Bfabric
from bfabric.entities import ExternalJob, Executable
from bfabric_scripts.cli.base import use_client


class SubmitterSlurm:
    def __init__(self, client: Bfabric, external_job: ExternalJob) -> None:
        self._client = client
        self._external_job = external_job
        self._workunit = external_job.workunit

    def get_workunit_wrapper_data(self) -> WorkunitWrapperData:
        # find the executable
        executables = Executable.find_by({"workunitid": self._workunit.id, "context": "WORKUNIT"}, client=self._client)
        if len(executables) != 1:
            msg = f"Expected exactly one WORKUNIT executable, found executables: {sorted(executables.keys())}"
            raise ValueError(msg)
        executable = list(executables.values())[0]

        # read the wrapper data
        yaml_data = base64.b64decode(executable["base64"].encode()).decode()
        return WorkunitWrapperData.model_validate(yaml.safe_load(yaml_data))

    def run(self) -> None:
        _workunit_wrapper_data = self.get_workunit_wrapper_data()
        # TODO so far it's not even slurm specific


@use_client
def app(*, client: Bfabric) -> None:
    """CLI interface for slurm submitter."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", type=int)
    args = parser.parse_args()
    external_job = ExternalJob.find(id=args.j, client=client)
    submitter = SubmitterSlurm(client=client, external_job=external_job)
    submitter.run()


if __name__ == "__main__":
    app()
