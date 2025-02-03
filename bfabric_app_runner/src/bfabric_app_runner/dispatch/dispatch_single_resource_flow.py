from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.experimental.workunit_definition import WorkunitDefinition
from loguru import logger
from pathlib import Path
from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.dispatch.generic import (
    write_chunks_file,
    write_workunit_definition_file,
)
from bfabric_app_runner.dispatch.resource_flow import get_resource_flow_input_resources


class ConfigDispatchSingleResourceFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filter_suffix: str | None = None


class DispatchSingleResourceFlow:
    def __init__(self, client: Bfabric, config: ConfigDispatchSingleResourceFlow, out_dir: Path) -> None:
        self._client = client
        self._config = config
        self._out_dir = out_dir

    def dispatch_job(self, resources: list[Resource], workunit: WorkunitDefinition) -> Path:
        raise NotImplementedError

    def dispatch_workunit(self, definition: WorkunitDefinition) -> None:
        if not definition.execution.resources:
            logger.error("No resources found in workunit.")
            return
        resources = get_resource_flow_input_resources(
            client=self._client,
            definition=definition,
            filter_suffix=self._config.filter_suffix,
        )
        write_workunit_definition_file(out_dir=self._out_dir, definition=definition)
        path = self.dispatch_job(resources=resources, workunit=definition)
        write_chunks_file(out_dir=self._out_dir, chunks=[path])
