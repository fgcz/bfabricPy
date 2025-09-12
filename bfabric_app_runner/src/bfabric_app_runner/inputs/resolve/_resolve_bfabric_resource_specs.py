from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities import Resource, Storage
from bfabric_app_runner.inputs.resolve._common import get_file_source_and_filename
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec


class ResolveBfabricResourceSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricResourceSpec]) -> list[ResolvedFile]:
        """Convert resource specifications to file specifications."""
        if not specs:
            return []

        # Fetch all resources and their storage information in bulk
        resource_ids = [spec.id for spec in specs]
        resources = Resource.find_all(ids=resource_ids, client=self._client)
        storage_ids = sorted({resource["storage"]["id"] for resource in resources.values()})
        storages = Storage.find_all(ids=storage_ids, client=self._client)

        # Create the file specs
        result = []
        for resource_id, spec in zip(resource_ids, specs):
            resource = resources[resource_id]
            storage = storages[resource["storage"]["id"]]
            result.append(self._get_file_spec(spec=spec, resource=resource, storage=storage))

        return result

    def _get_file_spec(self, spec: BfabricResourceSpec, resource: Resource, storage: Storage) -> ResolvedFile:
        source, filename = get_file_source_and_filename(resource=resource, storage=storage, filename=spec.filename)
        return ResolvedFile(
            source=source,
            filename=filename,
            link=False,
            checksum=resource["filechecksum"] if spec.check_checksum else None,
        )
