from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec


class ResolveStaticYamlSpecs:
    def __call__(self, specs: list[StaticYamlSpec]) -> list[StaticFileSpec]:
        """Convert YAML specifications to file specifications."""
        return [StaticFileSpec(content=yaml.safe_dump(spec.data), filename=spec.filename) for spec in specs]
