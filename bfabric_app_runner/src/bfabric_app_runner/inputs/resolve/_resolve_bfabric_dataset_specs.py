from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

from bfabric.entities import Dataset

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
    from bfabric import Bfabric


class ResolveBfabricDatasetSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricDatasetSpec]) -> list[ResolvedStaticFile]:
        """Convert dataset specifications to file specifications."""
        if not specs:
            return []

        # Fetch all datasets in bulk
        dataset_ids = [spec.id for spec in specs]
        datasets = Dataset.find_all(ids=dataset_ids, client=self._client)

        # Resolve each dataset specification to its serialized content
        return [
            ResolvedStaticFile(
                content=self._get_content(dataset=datasets[dataset_id], spec=spec), filename=spec.filename
            )
            for dataset_id, spec in zip(dataset_ids, specs)
        ]

    def _get_content(self, dataset: Dataset, spec: BfabricDatasetSpec) -> str | bytes:
        if spec.format == "csv":
            return dataset.get_csv(separator=spec.separator)
        elif spec.format == "parquet":
            return dataset.get_parquet()
        else:
            assert_never(spec.format)
