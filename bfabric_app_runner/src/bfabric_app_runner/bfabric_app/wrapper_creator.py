from __future__ import annotations

import argparse
import base64
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from bfabric import Bfabric  # noqa: TC002
from bfabric.entities import ExternalJob
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.app_runner.resolve_app import resolve_app
from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from bfabric_app_runner.specs.app.app_spec import AppSpecTemplate
from bfabric_scripts.cli.base import use_client
from loguru import logger

if TYPE_CHECKING:
    from bfabric.entities import Workunit


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
        path = Path(self._workunit.application.executable["program"])
        app_spec_template = AppSpecTemplate.model_validate(yaml.safe_load(path.read_text()))
        app = self._workunit.application
        app_spec = app_spec_template.evaluate(app_id=str(app.id), app_name=app["name"])
        app_version = resolve_app(versions=app_spec, workunit_definition=workunit_definition)
        app_runner_version = app_spec.bfabric.app_runner
        return WorkunitWrapperData(
            workunit_definition=workunit_definition, app_version=app_version, app_runner_version=app_runner_version
        )

    def run(self) -> None:
        data = self.get_data()
        yaml_data = yaml.safe_dump(data.model_dump(mode="json"))
        logger.info("YAML data:\n{}", yaml_data)
        executable_data = {
            "context": "WORKUNIT",
            "name": "workunit_wrapper_data.yml",
            "status": "available",
            "workunitid": self._workunit.id,
            "base64": base64.b64encode(yaml_data.encode()).decode(),
        }
        result = self._client.save("executable", executable_data)
        logger.info("Executable registered: {}", result[0])
        # TODO detect and store errors
        self._client.save("externaljob", {"id": self._external_job.id, "status": "done"})


@use_client
def app(client: Bfabric) -> None:
    """Wrapper creator CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", type=int)
    args = parser.parse_args()
    external_job = ExternalJob.find(id=args.j, client=client)
    wrapper_creator = WrapperCreator(client=client, external_job=external_job)
    wrapper_creator.run()


if __name__ == "__main__":
    app()
