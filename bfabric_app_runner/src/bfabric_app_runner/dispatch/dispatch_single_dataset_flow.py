from pathlib import Path

from loguru import logger

from bfabric_app_runner.dispatch.generic import write_workunit_definition_file, write_chunks_file
from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.experimental.workunit_definition import WorkunitDefinition


class DispatchSingleDatasetFlow:
    def __init__(self, client: Bfabric, out_dir: Path) -> None:
        self._client = client
        self._out_dir = out_dir

    def dispatch_job(self, dataset: Dataset, workunit: WorkunitDefinition) -> Path:
        raise NotImplementedError

    def dispatch_workunit(self, workunit: WorkunitDefinition) -> None:
        if not workunit.execution.dataset:
            logger.error("No dataset found in workunit.")
            return

        dataset = Dataset.find(id=workunit.execution.dataset, client=self._client)
        write_workunit_definition_file(out_dir=self._out_dir, definition=workunit)
        path = self.dispatch_job(dataset=dataset, workunit=workunit)
        write_chunks_file(out_dir=self._out_dir, chunks=[path])
