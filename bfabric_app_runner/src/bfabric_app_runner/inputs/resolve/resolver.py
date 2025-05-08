from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, assert_never

from bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs import ResolveBfabricAnnotationSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_order_fasta_specs import ResolveBfabricOrderFastaSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_specs import ResolveBfabricResourceSpecs
from bfabric_app_runner.inputs.resolve._resolve_file_specs import ResolveFileSpecs
from bfabric_app_runner.inputs.resolve._resolve_static_file_specs import ResolveStaticFileSpecs
from bfabric_app_runner.inputs.resolve._resolve_static_yaml_specs import ResolveStaticYamlSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import (
    BfabricAnnotationSpec,
)
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs_spec import InputSpecType


class Resolver:
    """Resolves input specifications into standardized file specifications."""

    def __init__(self, client: Bfabric) -> None:
        self._client = client
        self._resolve_bfabric_dataset_specs = ResolveBfabricDatasetSpecs(client=client)
        self._resolve_bfabric_resource_specs = ResolveBfabricResourceSpecs(client=client)
        self._resolve_static_yaml_specs = ResolveStaticYamlSpecs()
        self._resolve_static_file_specs = ResolveStaticFileSpecs()
        self._resolve_bfabric_order_fasta_specs = ResolveBfabricOrderFastaSpecs(client=client)
        self._resolve_bfabric_annotation_specs = ResolveBfabricAnnotationSpecs(client=client)
        self._resolve_file_specs = ResolveFileSpecs()

    def resolve(self, specs: list[InputSpecType]) -> ResolvedInputs:
        """Convert input specifications to resolved file specifications."""
        grouped_specs = self._group_specs_by_type(specs=specs)
        files = []

        for spec_type, specs_list in grouped_specs.items():
            if issubclass(spec_type, StaticYamlSpec):
                files.extend(self._resolve_static_yaml_specs(specs_list))
            elif issubclass(spec_type, StaticFileSpec):
                files.extend(self._resolve_static_file_specs(specs_list))
            elif issubclass(spec_type, BfabricResourceSpec):
                files.extend(self._resolve_bfabric_resource_specs(specs_list))
            elif issubclass(spec_type, BfabricDatasetSpec):
                files.extend(self._resolve_bfabric_dataset_specs(specs_list))
            elif issubclass(spec_type, BfabricOrderFastaSpec):
                files.extend(self._resolve_bfabric_order_fasta_specs(specs_list))
            elif issubclass(spec_type, BfabricAnnotationSpec):
                files.extend(self._resolve_bfabric_annotation_specs(specs_list))
            elif issubclass(spec_type, FileSpec):
                files.extend(self._resolve_file_specs(specs_list))
            else:
                assert_never(spec_type)

        return ResolvedInputs(files=files)

    @staticmethod
    def _group_specs_by_type(specs: list[InputSpecType]) -> dict[type, list]:
        """Group specifications by their type."""
        grouped = defaultdict(list)
        for spec in specs:
            grouped[type(spec)].append(spec)
        return grouped
