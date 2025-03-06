from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec


class ResolveStaticYamlSpecs:
    def __call__(self, specs: list[StaticYamlSpec]) -> list[ResolvedStaticFile]:
        """Convert YAML specifications to file specifications."""
        return [ResolvedStaticFile(content=yaml.safe_dump(spec.data), filename=spec.filename) for spec in specs]
