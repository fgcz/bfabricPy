from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from bfabric import Bfabric  # noqa: TC002
from bfabric.entities import ExternalJob
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.app_runner.resolve_app import resolve_app
from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from bfabric_app_runner.specs.app.app_spec import AppSpecTemplate
from loguru import logger

if TYPE_CHECKING:
    from bfabric.entities import Workunit


class WrapperCreator:
    """The wrapper creator is given the ID of an external job (WRAPPERCREATOR context) referencing a workunit.

    It generates the `app_definition.yml` and `workunit_definition.yml` structures and puts them into the WORKUNIT
    context executable, which will then be picked up by the submitter in the next step.
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
        path = Path(self._workunit.application.executable["program"])
        logger.info("Reading app spec from: {}", path)
        app_spec_template = AppSpecTemplate.model_validate(yaml.safe_load(path.read_text()))
        app = self._workunit.application
        app_spec = app_spec_template.evaluate(app_id=app.id, app_name=app["name"])
        app_version = resolve_app(versions=app_spec, workunit_definition=workunit_definition)
        app_runner_version = app_spec.bfabric.app_runner
        return WorkunitWrapperData(
            workunit_definition=workunit_definition, app_version=app_version, app_runner_version=app_runner_version
        )


@use_client
@logger.catch(reraise=True)
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
