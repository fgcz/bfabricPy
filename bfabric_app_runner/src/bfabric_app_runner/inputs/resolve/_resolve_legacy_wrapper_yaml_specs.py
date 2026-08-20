from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile
from bfabric_app_runner.legacy.wrapper_yaml import build_legacy_wrapper_yaml

if TYPE_CHECKING:
    from bfabric import Bfabric

    from bfabric_app_runner.specs.inputs.legacy_wrapper_yaml_spec import LegacyWrapperYamlSpec


class ResolveLegacyWrapperYamlSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client: Bfabric = client

    def __call__(self, specs: list[LegacyWrapperYamlSpec]) -> list[ResolvedStaticFile]:
        """Convert legacy wrapper YAML specifications to file specifications."""
        return [ResolvedStaticFile(filename=spec.filename, content=self._render(spec=spec)) for spec in specs]

    def _render(self, spec: LegacyWrapperYamlSpec) -> str:
        config = build_legacy_wrapper_yaml(
            client=self._client,
            workunit_id=spec.workunit_id,
            output_path=spec.output_path,
            executable=spec.executable,
        )
        return yaml.safe_dump(config)
