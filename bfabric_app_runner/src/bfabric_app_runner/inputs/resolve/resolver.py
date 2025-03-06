from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bfabric_app_runner.input_preparation.collect_annotation import get_annotation
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_order_fasta_specs import ResolveBfabricOrderFastaSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_specs import ResolveBfabricResourceSpecs
from bfabric_app_runner.inputs.resolve._resolve_static_yaml_specs import ResolveStaticYamlSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
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
        self._resolve_bfabric_order_fasta_specs = ResolveBfabricOrderFastaSpecs(client=client)

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

    def _resolve_bfabric_annotation_specs(self, specs: list[BfabricAnnotationSpec]) -> list[StaticFileSpec]:
        """Convert annotation specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [
            StaticFileSpec(content=get_annotation(spec=spec, client=self._client), filename=spec.filename)
            for spec in specs
        ]
