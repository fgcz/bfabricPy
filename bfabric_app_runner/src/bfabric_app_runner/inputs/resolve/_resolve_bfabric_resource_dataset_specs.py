from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING


from bfabric.entities import Dataset, Resource
from bfabric_app_runner.inputs._filter_files import filter_files
from bfabric_app_runner.inputs.resolve._common import get_file_source_and_filename
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile

if TYPE_CHECKING:
    from bfabric import Bfabric
    import polars as pl
    from bfabric_app_runner.specs.inputs.bfabric_resource_dataset import BfabricResourceDatasetSpec


class ResolveBfabricResourceDatasetSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricResourceDatasetSpec]) -> list[ResolvedFile]:
        # Note: We process each dataset spec individually here, this could be optimized should it become necessary
        #       in the future.
        return [file for spec in specs for file in self._resolve_spec(spec)]

    def _resolve_spec(self, spec: BfabricResourceDatasetSpec) -> list[ResolvedFile]:
        # TODO this will raise, but i am not sure how we handle errors at the moment
        dataset = Dataset.find(id=spec.id, client=self._client).to_polars()
        column = self._select_input_column(dataset, spec.column)
        resource_ids = dataset[column].unique().sort().to_list()
        resources_all = list(Resource.find_all(ids=resource_ids, client=self._client).values())
        resources_sel = filter_files(
            files=resources_all,
            include_patterns=spec.include_patterns,
            exclude_patterns=spec.exclude_patterns,
            key="relativepath",
        )
        files = []
        for resource in resources_sel:
            # TODO ensure storage is fetched only once per storage id
            source, filename = get_file_source_and_filename(resource=resource, storage=resource.storage, filename=None)
            files.append(
                ResolvedFile(
                    filename=str(Path(spec.filename) / filename),
                    source=source,
                    link=False,
                    checksum=resource["filechecksum"],
                )
            )
        return files

    def _resolve_unfiltered_dataset(self, spec: BfabricResourceDatasetSpec) -> pl.DataFrame:
        # Obtain dataset information
        data = Dataset.find(id=spec.id, client=self._client).to_polars()
        input_column = self._select_input_column(data, spec.column)

        # Obtain resource information
        resource_ids = self._extract_resource_ids(data, input_column)
        resources = [
            {"resource_id": r.id, "resource_filename": r}
            for r in Resource.find_all(ids=resource_ids, client=self._client).values()
        ]
        # TODO
        _ = resources

    def _select_input_column(self, dataset: pl.DataFrame, column: str | int) -> str | None:
        if isinstance(column, int):
            if 0 <= column < len(dataset.columns):
                return dataset.columns[column]
        elif isinstance(column, str):
            for c in dataset.columns:
                if c.lower() == column.lower():
                    return c
        return None

    def _extract_resource_ids(self, dataset: pl.DataFrame, column: str) -> list[int]:
        ids = dataset[column].unique().sort().to_list()
        if any(not isinstance(id, int) for id in ids):
            # TODO error handling
            msg = f"Column '{column}' contains non-integer values: {ids}"
            raise ValueError(msg)
        return ids
