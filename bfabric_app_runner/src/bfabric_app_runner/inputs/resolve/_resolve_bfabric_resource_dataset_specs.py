from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from bfabric.entities import Dataset, Resource
from bfabric_app_runner.inputs._filter_files import filter_dataframe
from bfabric_app_runner.inputs.resolve._common import get_file_source
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile, ResolvedStaticFile

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_resource_dataset import BfabricResourceDatasetSpec


class ResolveBfabricResourceDatasetSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricResourceDatasetSpec]) -> list[ResolvedFile | ResolvedStaticFile]:
        # Note: We process each spec individually here, this could be optimized should it become necessary
        #       in the future.
        return [file for spec in specs for file in self._resolve_spec(spec)]

    def _resolve_spec(self, spec: BfabricResourceDatasetSpec) -> list[ResolvedFile | ResolvedStaticFile]:
        data_tmp = self._resolve_unfiltered_dataset(spec=spec)
        data_filtered = self._filter_dataset(spec=spec, data=data_tmp)
        output_file_column = self._get_unique_output_column(spec, data_filtered)
        data = data_filtered.rename({"tmp_resource_filename": output_file_column}).drop(
            "tmp_resource_source", "tmp_resource_relative_path", "tmp_resource_checksum"
        )

        files: list[ResolvedFile | ResolvedStaticFile] = [
            ResolvedStaticFile(
                filename=str(Path(spec.filename) / spec.output_dataset_filename), content=self._data_to_parquet(data)
            )
        ]
        if not spec.output_dataset_only:
            files.extend(
                ResolvedFile(
                    filename=str(Path(spec.filename) / row["tmp_resource_filename"]),  # pyright:ignore[reportAny]
                    source=row["tmp_resource_source"],  # pyright:ignore[reportAny]
                    link=False,
                    checksum=row["tmp_resource_checksum"],  # pyright:ignore[reportAny]
                )
                for row in data_filtered.iter_rows(named=True)
            )
        return files

    def _get_unique_output_column(self, spec: BfabricResourceDatasetSpec, data: pl.DataFrame) -> str:
        output_file_column = spec.output_dataset_file_column
        if output_file_column not in data.columns:
            return output_file_column
        for i in range(1, 10):
            candidate = f"{output_file_column}.{i}"
            if candidate not in data.columns:
                return candidate
        raise ValueError("Could not determine unique output file column name.")

    @staticmethod
    def _data_to_parquet(data: pl.DataFrame) -> bytes:
        with BytesIO() as stream:
            data.write_parquet(file=stream)
            return stream.getvalue()

    def _filter_dataset(self, spec: BfabricResourceDatasetSpec, data: pl.DataFrame) -> pl.DataFrame:
        return filter_dataframe(
            data,
            column="tmp_resource_relative_path",
            include_patterns=spec.include_patterns,
            exclude_patterns=spec.exclude_patterns,
        )

    def _resolve_unfiltered_dataset(self, spec: BfabricResourceDatasetSpec) -> pl.DataFrame:
        """Resolves the original dataframe with extra columns
        - tmp_resource_filename: The filename of the resource
        - tmp_resource_relative_path: The relative path of the resource in storage
        - tmp_resource_checksum: The checksum of the resource file
        - tmp_resource_source: The source (URL or local path) of the resource
        """
        # Obtain dataset information
        data = Dataset.find(id=spec.id, client=self._client).to_polars()
        input_column = self._select_input_column(data, spec.column)
        data = data.with_columns(pl.col(input_column).cast(pl.Int64))

        # Obtain resource information
        resource_ids = self._extract_resource_ids(data, input_column)
        resources = [
            {
                "resource_id": r.id,
                "tmp_resource_filename": r.filename,
                "tmp_resource_checksum": r["filechecksum"],
                "tmp_resource_relative_path": r.storage_relative_path,
                "tmp_resource_source": get_file_source(r),
            }
            for r in Resource.find_all(ids=resource_ids, client=self._client).values()
        ]

        # Merge
        return data.join(pl.DataFrame(resources), left_on=input_column, right_on="resource_id", how="left")

    @staticmethod
    def _extract_resource_ids(dataset: pl.DataFrame, column: str) -> list[int]:
        return dataset[column].unique().sort().to_list()

    @staticmethod
    def _select_input_column(dataset: pl.DataFrame, column: str | int) -> str | None:
        if isinstance(column, int):
            if 0 <= column < len(dataset.columns):
                return dataset.columns[column]
        elif isinstance(column, str):
            for c in dataset.columns:
                if c.lower() == column.lower():
                    return c
        return None
