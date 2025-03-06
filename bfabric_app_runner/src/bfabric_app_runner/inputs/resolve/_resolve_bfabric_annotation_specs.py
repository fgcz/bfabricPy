from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric_app_runner.input_preparation.collect_annotation import get_annotation
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec


class ResolveBfabricAnnotationSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricAnnotationSpec]) -> list[ResolvedStaticFile]:
        """Convert annotation specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [
            ResolvedStaticFile(content=get_annotation(spec=spec, client=self._client), filename=spec.filename)
            for spec in specs
        ]
