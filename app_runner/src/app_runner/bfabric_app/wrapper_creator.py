from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import cyclopts
import yaml
from cyclopts import Parameter
from loguru import logger

from app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from app_runner.specs.app.app_spec import AppSpecTemplate
from bfabric.entities import ExternalJob
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_scripts.cli.base import use_client

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Workunit


# TODO error handling


class WrapperCreator:
    """The wrapper creator is given the ID of an external job (WRAPPERCREATOR context) referencing a workunit.

    What this script is responsible for is to obtain the `app_definition.yml` and the `workunit_definition.yml`, and
    register these in B-Fabric as a WORKUNIT context executable which will then be picked up by the submitter in the
    next step.
    """

    def __init__(self, client: Bfabric, external_job: ExternalJob) -> None:
        self._client = client
        self._external_job = external_job

    @property
    def _workunit(self) -> Workunit:
        return self._external_job.workunit

    def get_data(self) -> WorkunitWrapperData:
        """Returns the data to be written to WORKUNIT context executable."""
        workunit_definition = WorkunitDefinition.from_workunit(workunit=self._workunit)
        # TODO could this be made more robust in the future, e.g. by specifying the root path somehow?
        path = Path(self._workunit.application["program"])
        application_definition = AppSpecTemplate.model_validate(yaml.safe_load(path.read_text()))
        return WorkunitWrapperData(workunit=workunit_definition, app=application_definition)

    def run(self) -> None:
        data = self.get_data()
        yaml_data = yaml.safe_dump(data.model_dump(mode="json"))
        logger.info("YAML data: {}", yaml_data)
        executable_data = {
            "context": "WORKUNIT",
            "parameters": [],
            "status": "available",
            "base64": base64.b64encode(yaml_data.encode()).decode(),
        }
        self._client.save("executable", executable_data)


# TODO move this if necessary, it's here for testing right now

app = cyclopts.App()


@app.default
@use_client
def interface(j: Annotated[int, Parameter(name="-j")], *, client: Bfabric) -> None:
    """Wrapper creator CLI."""
    external_job = ExternalJob.find(id=j, client=client)
    wrapper_creator = WrapperCreator(external_job=external_job)
    wrapper_creator.run()


if __name__ == "__main__":
    app()
