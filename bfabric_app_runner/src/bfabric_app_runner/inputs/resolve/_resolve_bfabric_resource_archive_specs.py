from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory
from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceSshValue

from bfabric.entities import Resource, Storage

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec import BfabricResourceArchiveSpec


class ResolveBfabricResourceArchiveSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricResourceArchiveSpec]) -> list[ResolvedDirectory]:
        """Convert resource archive specifications to directory specifications."""
        if not specs:
            return []

        # Fetch all resources and their storage information in bulk
        resource_ids = [spec.id for spec in specs]
        resources = Resource.find_all(ids=resource_ids, client=self._client)
        storage_ids = sorted({resource["storage"]["id"] for resource in resources.values()})
        storages = Storage.find_all(ids=storage_ids, client=self._client)

        # Create the directory specs
        result = []
        for resource_id, spec in zip(resource_ids, specs):
            resource = resources[resource_id]
            storage = storages[resource["storage"]["id"]]
            result.append(self._get_directory_spec(spec=spec, resource=resource, storage=storage))

        return result

    def _get_directory_spec(
        self, spec: BfabricResourceArchiveSpec, resource: Resource, storage: Storage
    ) -> ResolvedDirectory:
        return ResolvedDirectory(
            source=FileSourceSsh(
                ssh=FileSourceSshValue(host=storage["host"], path=f"{storage['basepath']}{resource['relativepath']}")
            ),
            filename=spec.filename,
            extract=spec.extract,
            include_patterns=spec.include_patterns,
            exclude_patterns=spec.exclude_patterns,
            strip_root=spec.strip_root,
            checksum=resource["filechecksum"] if spec.check_checksum else None,
        )
