from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict, model_validator

from bfabric import Bfabric
from bfabric.entities import Resource, Dataset
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
    def check_at_least_one_flow(self) -> Self:
        if self.resource_flow is None and self.dataset_flow is None:
            raise ValueError("either resource_flow or dataset_flow must be provided")
        return self


def config_msi_imzml() -> ConfigDispatchIndividualResources:
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
        self._write_workunit_definition(definition=definition)
        self._write_chunks(chunks=paths)

    def _write_workunit_definition(self, definition: WorkunitDefinition) -> None:
        self._out_dir.mkdir(exist_ok=True, parents=True)
        with (self._out_dir / "workunit_definition.yml").open("w") as f:
            yaml.safe_dump(definition.model_dump(mode="json"), f)

    def _write_chunks(self, chunks: list[Path]) -> None:
        self._out_dir.mkdir(exist_ok=True, parents=True)
        with (self._out_dir / "chunks.yml").open("w") as f:
            data = {"chunks": [str(chunk) for chunk in chunks]}
            yaml.safe_dump(data, f)

    def _dispatch_jobs_resource_flow(self, definition: WorkunitDefinition, params: dict[str, Any]) -> list[Path]:
        if self._config.resource_flow is None:
            raise ValueError("resource_flow is not configured")
        resources = Resource.find_all(ids=definition.execution.resources, client=self._client)
        paths = []
        for resource in sorted(resources.values()):
            if self._config.resource_flow.filter_suffix is not None and not resource["relativepath"].endswith(
                self._config.resource_flow.filter_suffix
            ):
                logger.info(
                    f"Skipping resource {resource['relativepath']!r} as it does not match the extension filter."
                )
                continue
            paths.append(self.dispatch_job(resource=resource, params=params))
        return paths

    def _dispatch_jobs_dataset_flow(self, definition: WorkunitDefinition, params: dict[str, Any]) -> list[Path]:
        if self._config.dataset_flow is None:
            raise ValueError("dataset_flow is not configured")
        dataset = Dataset.find(id=definition.execution.dataset, client=self._client)
        dataset_df = dataset.to_polars()
        resources = Resource.find_all(
            ids=dataset_df[self._config.dataset_flow.resource_column].unique().to_list(), client=self._client
        )
        paths = []
        for row in dataset_df.iter_rows(named=True):
            resource_id = int(row[self._config.dataset_flow.resource_column])
            row_params = {name: row[dataset_name] for dataset_name, name in self._config.dataset_flow.param_columns}
            paths.append(self.dispatch_job(resource=resources[resource_id], params=params | row_params))
        return paths
