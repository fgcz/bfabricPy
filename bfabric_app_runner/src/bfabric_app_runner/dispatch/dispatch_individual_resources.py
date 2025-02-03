from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, model_validator

from bfabric_app_runner.dispatch.generic import write_workunit_definition_file, write_chunks_file
from bfabric_app_runner.dispatch.resource_flow import get_resource_flow_input_resources
from bfabric.entities import Resource, Dataset

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from bfabric.experimental.workunit_definition import WorkunitDefinition


class ConfigResourceFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filter_suffix: str | None = None


class ConfigDatasetFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_column: str = "Imzml"
    param_columns: list[tuple[str, str]] = [("PanelDataset", "mass_list_id")]


class ConfigDispatchIndividualResources(BaseModel):
    resource_flow: ConfigResourceFlow | None
    dataset_flow: ConfigDatasetFlow | None

    @model_validator(mode="after")
    def check_at_least_one_flow(self) -> ConfigDispatchIndividualResources:
        if self.resource_flow is None and self.dataset_flow is None:
            raise ValueError("either resource_flow or dataset_flow must be provided")
        return self


def config_msi_imzml() -> ConfigDispatchIndividualResources:
    """Returns the configuration for dispatching MSI imzML datasets to chunks.

    These apps allow both being run with a list of input `.imzML` resource files, or a dataset which contains a column
    `Imzml` with the resource IDs and a column `PanelDataset` with the dataset IDs.

    Note: In the future the specifics of this might be adapted to allow e.g. `.imzML.7z` files or similar.
    """
    return ConfigDispatchIndividualResources(
        resource_flow=ConfigResourceFlow(filter_suffix=".imzML"),
        dataset_flow=ConfigDatasetFlow(resource_column="Imzml", param_columns=[("PanelDataset", "mass_list_id")]),
    )


class DispatchIndividualResources:
    """Dispatches jobs on individual resources specified in the workunit."""

    def __init__(self, client: Bfabric, config: ConfigDispatchIndividualResources, out_dir: Path) -> None:
        self._client = client
        self._config = config
        self._out_dir = out_dir

    def dispatch_job(self, resource: Resource, params: dict[str, Any]) -> Path:
        # TODO it is not clear yet if this is the best approach to handle this by inheritance here,
        #      I would sort of prefer to decouple this but it's not fully clear how to do it and it would not always
        #      be possible to do this as generically
        # -> maybe in an initial version we can handle it with python code, but in the future revisit if it might make
        #    more sense to be even more generic there
        raise NotImplementedError

    def dispatch_workunit(self, definition: WorkunitDefinition) -> None:
        params = definition.execution.raw_parameters
        if definition.execution.resources:
            paths = self._dispatch_jobs_resource_flow(definition, params)
        elif definition.execution.dataset:
            paths = self._dispatch_jobs_dataset_flow(definition, params)
        else:
            raise ValueError("either dataset or resources must be provided")
        write_workunit_definition_file(out_dir=self._out_dir, definition=definition)
        write_chunks_file(out_dir=self._out_dir, chunks=paths)

    def _dispatch_jobs_resource_flow(self, definition: WorkunitDefinition, params: dict[str, Any]) -> list[Path]:
        """Returns the individual jobs for a resource flow workunit and returns the paths of the task folders."""
        config = self._config.resource_flow
        if config is None:
            raise ValueError("resource_flow is not configured")
        resources = get_resource_flow_input_resources(
            client=self._client, definition=definition, filter_suffix=config.filter_suffix
        )
        return [self.dispatch_job(resource=resource, params=params) for resource in resources]

    def _dispatch_jobs_dataset_flow(self, definition: WorkunitDefinition, params: dict[str, Any]) -> list[Path]:
        config = self._config.dataset_flow
        if config is None:
            raise ValueError("dataset_flow is not configured")
        dataset = Dataset.find(id=definition.execution.dataset, client=self._client)
        if dataset is None:
            msg = f"Dataset with id {definition.execution.dataset} not found"
            raise ValueError(msg)
        dataset_df = dataset.to_polars()
        resources = Resource.find_all(ids=dataset_df[config.resource_column].unique().to_list(), client=self._client)
        paths = []
        for row in dataset_df.iter_rows(named=True):
            resource_id = int(row[config.resource_column])
            row_params = {name: row[dataset_name] for dataset_name, name in config.param_columns}
            paths.append(self.dispatch_job(resource=resources[resource_id], params=params | row_params))
        return paths
