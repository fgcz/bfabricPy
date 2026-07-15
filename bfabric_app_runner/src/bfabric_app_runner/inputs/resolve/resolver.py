from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, get_args

from bfabric.entities.cache.context import cache_entities
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
        # Maps each concrete input-spec class to the resolver handling it. Adding an input type is a
        # single new entry here (plus its spec model, InputSpecType union member, and resolver class).
        # The parameter type of each resolver is elided (``...``) because each accepts a different
        # spec subtype; the registry keys carry the routing information instead.
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
        with cache_entities(entities=["application", "dataset", "resource", "storage"], max_size=500):
            files: list[ResolvedInput] = []
            for spec_type, specs_list in self._group_specs_by_type(specs=specs).items():
                files.extend(self._resolver_for(spec_type)(specs_list))
        return ResolvedInputs(files=files)

    def _resolver_for(self, spec_type: type) -> Callable[..., Sequence[ResolvedInput]]:
        """Return the resolver for a spec class, walking the MRO on an exact-key miss.

        The MRO walk (``issubclass``, not exact equality) keeps dispatch working if a registered base
        class (e.g. the ``BfabricAnnotationSpec`` family) ever becomes a union of concrete subtypes.
        """
        resolver = self._registry.get(spec_type)
        if resolver is not None:
            return resolver
        for base, candidate in self._registry.items():
            if issubclass(spec_type, base):
                return candidate
        raise TypeError(f"No resolver registered for input spec type {spec_type!r}")

    def _check_registry_exhaustive(self) -> None:
        """Fail loudly at construction if any ``InputSpecType`` member has no registered resolver."""
        # InputSpecType is ``Annotated[<union>, Field(...)]``; unwrap the annotation, then the union.
        members: tuple[type, ...] = get_args(get_args(InputSpecType)[0])
        missing = [member for member in members if not any(issubclass(member, base) for base in self._registry)]
        if missing:
            raise TypeError(f"Resolver registry is missing entries for input spec types: {missing!r}")

    @staticmethod
    def _group_specs_by_type(specs: list[InputSpecType]) -> dict[type, list[InputSpecType]]:
        """Group specifications by their concrete type."""
        grouped: dict[type, list[InputSpecType]] = defaultdict(list)
        for spec in specs:
            grouped[type(spec)].append(spec)
        return grouped
