from __future__ import annotations

from pathlib import Path  # noqa: TC001
from typing import Annotated, TYPE_CHECKING

import yaml
from bfabric_app_runner.specs.inputs.file_spec import FileSpec, FileSourceSsh, FileSourceSshValue
from pydantic import BaseModel, Field

from bfabric.entities import Resource, Storage, Dataset
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
    from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
    from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
    from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
    from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec

# TODO The current logic will simply put all "StaticFile" content into RAM, which is generally fine for now,
#      but if we ever need to change this i guess we will want to have some type of off-loading into a tmp file that
#      can be referenced, maybe with an additional ResolvedSpecType

ResolvedSpecType = Annotated[FileSpec | StaticFileSpec, Field(discriminator="type")]


class InputListingFile(BaseModel):
    filename: Path
    spec: ResolvedSpecType


class InputListing(BaseModel):
    files: list[InputListingFile]


# TODO the transforms should be bundled into a class, or, their interface will need to be standardized to some extent
#   ->but the code calling them will decide


def transform_static_yaml_specs(specs: list[StaticYamlSpec]) -> list[StaticFileSpec]:
    """Transforms a list of StaticYamlSpecs into a list of StaticFileSpecs."""
    # TODO this is just one example
    return [StaticFileSpec(content=yaml.safe_dump(spec.data), filename=spec.filename) for spec in specs]


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


def transform_bfabric_dataset_specs(specs: list[BfabricDatasetSpec], client: Bfabric) -> list[StaticFileSpec]:
    """Transforms a list of BfabricDatasetSpecs into a list of StaticFileSpecs."""
    dataset_ids = [spec.id for spec in specs]
    datasets = Dataset.find_all(ids=dataset_ids, client=client)
    transformed = []
    for spec, dataset_id in zip(specs, dataset_ids):
        dataset = datasets[dataset_id]
        if spec.format == "csv":
            dataset_content = dataset.get_csv(separator=spec.separator)
        elif spec.format == "parquet":
            dataset_content = dataset.get_parquet()
        else:
            raise NotImplementedError(f"Unsupported dataset format: {spec.format}")

        transformed.append(StaticFileSpec(content=dataset_content, filename=spec.filename))
    return transformed


def transform_bfabric_order_fasta_spec(specs: list[BfabricOrderFastaSpec], client: Bfabric) -> list[StaticFileSpec]:
    """Transforms a list of BfabricOrderFastaSpecs into a list of StaticFileSpecs."""
    transformed = []
    for spec in specs:
        # TODO should be easy to reuse the existing functionality
        raise NotImplementedError
    return transformed


def transform_bfabric_annotation_spec(specs: list[BfabricAnnotationSpec], client: Bfabric) -> list[StaticFileSpec]:
    """Transforms a list of BfabricAnnotationSpecs into a list of StaticFileSpecs."""
    transformed = []
    for spec in specs:
        # TODO should be easy to reuse the existing functionality
        raise NotImplementedError
    return transformed
