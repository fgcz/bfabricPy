from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from bfabric_app_runner.input_preparation.collect_annotation import get_annotation
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs
from bfabric_app_runner.inputs.resolve.get_order_fasta import get_order_fasta
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSpec, FileSourceSsh, FileSourceSshValue
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec

from bfabric.entities import Resource, Storage

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs_spec import InputSpecType


class Resolver:
    """Resolves input specifications into standardized file specifications."""

    def __init__(self, client: Bfabric) -> None:
        self._client = client
        self._resolve_bfabric_dataset_specs = ResolveBfabricDatasetSpecs(client=client)

    def resolve(self, specs: list[InputSpecType]) -> ResolvedInputs:
        """Convert input specifications to resolved file specifications."""
        grouped_specs = self._group_specs_by_type(specs)
        files = []

        for spec_type, specs_list in grouped_specs.items():
            match spec_type:
                case StaticYamlSpec():
                    files.extend(self._resolve_static_yaml_specs(specs_list))
                case BfabricResourceSpec():
                    files.extend(self._resolve_bfabric_resource_specs(specs_list))
                case BfabricDatasetSpec():
                    files.extend(self._resolve_bfabric_dataset_specs(specs_list))
                case BfabricOrderFastaSpec():
                    files.extend(self._resolve_bfabric_order_fasta_specs(specs_list))
                case BfabricAnnotationSpec():
                    files.extend(self._resolve_bfabric_annotation_specs(specs_list))
                case _:
                    raise ValueError(f"Unsupported specification type: {spec_type.__name__}")

        return ResolvedInputs(files=files)

    @staticmethod
    def _group_specs_by_type(specs: list[InputSpecType]) -> dict[type, list]:
        """Group specifications by their type."""
        grouped = defaultdict(list)
        for spec in specs:
            grouped[type(spec)].append(spec)
        return grouped

    @staticmethod
    def _resolve_static_yaml_specs(specs: list[StaticYamlSpec]) -> list[StaticFileSpec]:
        """Convert YAML specifications to file specifications."""
        return [StaticFileSpec(content=yaml.safe_dump(spec.data), filename=spec.filename) for spec in specs]

    def _resolve_bfabric_resource_specs(self, specs: list[BfabricResourceSpec]) -> list[FileSpec]:
        """Convert resource specifications to file specifications."""
        if not specs:
            return []

        # Fetch all resources and their storage information in bulk
        resource_ids = [spec.id for spec in specs]
        resources = Resource.find_all(ids=resource_ids, client=self._client)

        storage_ids = [resource["storage"]["id"] for resource in resources.values()]
        storages = Storage.find_all(ids=storage_ids, client=self._client)

        # Create file specs
        result = []
        for spec in specs:
            resource = resources.get(spec.id)
            if not resource:
                msg = f"Resource {spec.id} not found"
                raise ValueError(msg)

            storage_id = resource["storage"]["id"]
            storage = storages[storage_id]

            result.append(
                FileSpec(
                    source=FileSourceSsh(
                        ssh=FileSourceSshValue(
                            host=storage["host"], path=f"{storage['basepath']}{resource['relativepath']}"
                        )
                    ),
                    filename=spec.filename or Path(resource["relativepath"]).name,
                    link=False,
                    checksum=resource["filechecksum"] if spec.check_checksum else None,
                )
            )

        return result

    def _resolve_bfabric_order_fasta_specs(self, specs: list[BfabricOrderFastaSpec]) -> list[StaticFileSpec]:
        """Convert order FASTA specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [
            StaticFileSpec(content=get_order_fasta(spec=spec, client=self._client), filename=spec.filename)
            for spec in specs
        ]

    def _resolve_bfabric_annotation_specs(self, specs: list[BfabricAnnotationSpec]) -> list[StaticFileSpec]:
        """Convert annotation specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [
            StaticFileSpec(content=get_annotation(spec=spec, client=self._client), filename=spec.filename)
            for spec in specs
        ]
