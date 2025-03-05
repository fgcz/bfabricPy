from __future__ import annotations

from pathlib import Path  # noqa: TC001
from typing import Annotated, TYPE_CHECKING

import yaml
from bfabric_app_runner.specs.inputs.file_spec import FileSpec, FileSourceSsh, FileSourceSshValue
from pydantic import BaseModel, Field

from bfabric.entities import Resource, Storage
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
    from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec

ResolvedSpecType = Annotated[FileSpec | StaticFileSpec, Field(discriminator="type")]


class InputListingFile(BaseModel):
    filename: Path
    spec: ResolvedSpecType


class InputListing(BaseModel):
    files: list[InputListingFile]


def transform_static_yaml_specs(specs: list[StaticYamlSpec]) -> list[StaticFileSpec]:
    """Transforms a list of StaticYamlSpecs into a list of StaticFileSpecs."""
    # TODO this is just one example
    return [StaticFileSpec(text=yaml.safe_dump(spec.data), filename=spec.filename) for spec in specs]


def transform_bfabric_resource_specs(specs: list[BfabricResourceSpec], client: Bfabric) -> list[FileSpec]:
    """Transforms a list of BfabricResourceSpecs into a list of FileSpecs."""
    resource_ids = [spec.id for spec in specs]
    resources = Resource.find_all(ids=resource_ids, client=client)
    # TODO we could use .storage.id but i want to ensure it does not trigger a new request first
    storage_ids = [resource["storage"]["id"] for resource in resources]
    storages = Storage.find_all(ids=storage_ids, client=client)

    transformed = []
    for spec, resource_id in zip(specs, resource_ids):
        # get loaded entities
        resource = resources[resource_id]
        # TODO see above .storage.id
        storage = storages[resource["storage"]["id"]]

        # determine metadata
        filename = spec.filename if spec.filename is not None else Path(resource["relativepath"]).name
        checksum = resource["filechecksum"] if spec.check_checksum else None

        # determine ssh information
        ssh_host = storage["host"]
        ssh_path = f"{storage['basepath']}{resource['relativepath']}"

        # put it all together into a FileSpec
        spec_source = FileSourceSsh(ssh=FileSourceSshValue(host=ssh_host, path=ssh_path))
        transformed.append(FileSpec(source=spec_source, filename=filename, link=False, checksum=checksum))

    return transformed
