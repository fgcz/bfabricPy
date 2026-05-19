from __future__ import annotations

from typing import TYPE_CHECKING, final

from bfabric.entities import Resource

from bfabric_app_runner.inputs.resolve._common import get_file_source
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile

if TYPE_CHECKING:
    from bfabric import Bfabric

    from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec


@final
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

        # Create the file specs
        result: list[ResolvedFile] = []
        for resource_id, spec in zip(resource_ids, specs):
            resource = resources[resource_id]
            result.append(self._get_file_spec(spec=spec, resource=resource))

        return result

    def _get_file_spec(self, spec: BfabricResourceSpec, resource: Resource) -> ResolvedFile:
        source = get_file_source(resource=resource)
        checksum = resource["filechecksum"] if spec.check_checksum else None
        if checksum is not None and not isinstance(checksum, str):
            raise ValueError(f"Invalid checksum type for resource {resource.id}: {type(checksum)}")
        return ResolvedFile(
            source=source,
            filename=spec.filename or resource.filename,
            link=False,
            checksum=checksum,
        )
