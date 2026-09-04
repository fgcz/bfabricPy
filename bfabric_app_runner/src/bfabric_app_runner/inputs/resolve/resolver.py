from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, get_args

from bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs import ResolveBfabricAnnotationSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_order_fasta_specs import ResolveBfabricOrderFastaSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_archive_specs import ResolveBfabricResourceArchiveSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_dataset_specs import ResolveBfabricResourceDatasetSpecs
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_specs import ResolveBfabricResourceSpecs
from bfabric_app_runner.inputs.resolve._resolve_file_specs import ResolveFileSpecs
from bfabric_app_runner.inputs.resolve._resolve_static_file_specs import ResolveStaticFileSpecs
from bfabric_app_runner.inputs.resolve._resolve_static_yaml_specs import ResolveStaticYamlSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInput, ResolvedInputs
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec import BfabricResourceArchiveSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_dataset_spec import BfabricResourceDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
from bfabric_app_runner.specs.inputs_spec import InputSpecType

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from bfabric import Bfabric


class Resolver:
    """Resolves input specifications into standardized file specifications."""

    def __init__(self, client: Bfabric) -> None:
        self._client: Bfabric = client
        # Adding an input type means one new entry here, alongside its spec model, its InputSpecType
        # union member and its resolver class. Each resolver takes a different spec subtype, so the
        # parameter type is elided (``...``) and the key carries the routing information.
        self._registry: dict[type, Callable[..., Sequence[ResolvedInput]]] = {
            StaticYamlSpec: ResolveStaticYamlSpecs(),
            StaticFileSpec: ResolveStaticFileSpecs(),
            FileSpec: ResolveFileSpecs(),
            BfabricResourceSpec: ResolveBfabricResourceSpecs(client=client),
            BfabricResourceArchiveSpec: ResolveBfabricResourceArchiveSpecs(client=client),
            BfabricResourceDatasetSpec: ResolveBfabricResourceDatasetSpecs(reader=client.reader),
            BfabricDatasetSpec: ResolveBfabricDatasetSpecs(reader=client.reader),
            BfabricOrderFastaSpec: ResolveBfabricOrderFastaSpecs(client=client),
            BfabricAnnotationSpec: ResolveBfabricAnnotationSpecs(client=client),
        }
        self._check_registry_exhaustive()

    def resolve(self, specs: list[InputSpecType]) -> ResolvedInputs:
        """Convert input specifications to resolved file specifications."""
        # Establish (or nest into) the read scope so entity navigation + caching work whether or not the
        # caller already opened one (e.g. the @use_client CLI decorator).
        with (
            self._client.reader as scope,
            scope.cache_entities(entities=["application", "dataset", "resource", "storage"], max_size=500),
        ):
            files: list[ResolvedInput] = []
            for spec_type, specs_list in self._group_specs_by_type(specs=specs).items():
                files.extend(self._registry[spec_type](specs_list))
        return ResolvedInputs(files=files)

    def _check_registry_exhaustive(self) -> None:
        """Fail at construction, rather than part-way through a resolve, if a spec type has no resolver.

        Specs are grouped by their runtime ``type()``, so a new ``InputSpecType`` member needs its own
        entry even when it subclasses one that is already registered.
        """
        # InputSpecType is ``Annotated[<union>, Field(...)]``: unwrap the annotation, then the union.
        members: tuple[type, ...] = get_args(get_args(InputSpecType)[0])
        missing = [member for member in members if member not in self._registry]
        if missing:
            raise TypeError(f"Resolver registry is missing entries for input spec types: {missing!r}")

    @staticmethod
    def _group_specs_by_type(specs: list[InputSpecType]) -> dict[type, list[InputSpecType]]:
        """Group specifications by their concrete type."""
        grouped: dict[type, list[InputSpecType]] = defaultdict(list)
        for spec in specs:
            grouped[type(spec)].append(spec)
        return grouped
