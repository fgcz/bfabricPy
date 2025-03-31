from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec


class ResolveStaticFileSpecs:
    def __call__(self, specs: list[StaticFileSpec]) -> list[ResolvedStaticFile]:
        """Convert YAML specifications to file specifications."""
        return [ResolvedStaticFile(content=spec.content, filename=spec.filename) for spec in specs]
