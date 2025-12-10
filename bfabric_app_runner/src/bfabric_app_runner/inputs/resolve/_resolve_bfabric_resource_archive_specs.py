from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard, TypeVar, final

from bfabric.entities import Resource, Storage
from bfabric.entities.core.uri import EntityUri

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory
from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceSshValue

if TYPE_CHECKING:
    from bfabric import Bfabric

    from bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec import BfabricResourceArchiveSpec


@final
class ResolveBfabricResourceArchiveSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client
        self._reader = self._client.reader

    def __call__(self, specs: list[BfabricResourceArchiveSpec]) -> list[ResolvedDirectory]:
        """Convert resource archive specifications to directory specifications."""
        if not specs:
            return []

        resources = self._get_resources(specs)
        storage_uris = self._get_resource_storage_uris(resources)
        storages = self._reader.read_uris(storage_uris, expected_type=Storage)

        if not _no_none_value(storages):
            raise ValueError("Some storage URIs are invalid")

        specs_by_id = {spec.id: spec for spec in specs}

        # Create the directory specs
        result: list[ResolvedDirectory] = []
        # for resource_id, spec in zip(resource_ids, specs):
        for resource_uri, resource in resources.items():
            storage_uri = resource.refs.uris["storage"]
            if not isinstance(storage_uri, EntityUri):
                raise ValueError(f"Storage URI for resource {resource_uri} is not an EntityUri")
            storage = storages[storage_uri]
            spec = specs_by_id[resource.id]
            result.append(self._get_directory_spec(spec=spec, resource=resource, storage=storage))

        return result

    def _get_resources(self, specs: list[BfabricResourceArchiveSpec]) -> dict[EntityUri, Resource]:
        resource_ids = [spec.id for spec in specs]
        resources = self._reader.read_ids("resource", resource_ids, expected_type=Resource)
        if not _no_none_value(resources):
            raise ValueError("Some resource IDs are invalid")
        return resources

    def _get_resource_storage_uris(self, resources: dict[EntityUri, Resource]) -> list[EntityUri]:
        uris_list = [resource.refs.uris["storage"] for resource in resources.values()]
        if not _is_flat_uri_list(uris_list):
            raise ValueError("Storage URIs must be flat")
        return sorted(set(uris_list))

    def _get_directory_spec(
        self, spec: BfabricResourceArchiveSpec, resource: Resource, storage: Storage
    ) -> ResolvedDirectory:
        checksum = resource["filechecksum"] if spec.check_checksum else None

        if checksum is not None and not isinstance(checksum, str):
            raise ValueError("checksum must be a string")

        return ResolvedDirectory(
            source=self._get_file_source(resource=resource, storage=storage),
            filename=spec.filename,
            extract=spec.extract,
            include_patterns=spec.include_patterns,
            exclude_patterns=spec.exclude_patterns,
            strip_root=spec.strip_root,
            checksum=checksum,
        )

    @staticmethod
    def _get_file_source(resource: Resource, storage: Storage) -> FileSourceSsh:
        host = storage["host"]
        path = resource.storage_absolute_path

        if not isinstance(host, str):
            raise ValueError("host must be a string")

        return FileSourceSsh(ssh=FileSourceSshValue.model_validate({"host": host, "path": path}))


def _is_flat_uri_list(uris: list[EntityUri | list[EntityUri]]) -> TypeGuard[list[EntityUri]]:
    return all(isinstance(uri, EntityUri) for uri in uris)


K = TypeVar("K")
V = TypeVar("V")


def _no_none_value(values: dict[K, V | None]) -> TypeGuard[dict[K, V]]:
    return all(value is not None for value in values.values())
