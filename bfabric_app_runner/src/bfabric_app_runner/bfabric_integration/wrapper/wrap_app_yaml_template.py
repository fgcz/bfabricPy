from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mako.template
from loguru import logger
from pydantic import BaseModel


if TYPE_CHECKING:
    from bfabric.entities import Workunit


class WrapAppYamlTemplate:
    class Params(BaseModel):
        class Dependencies(BaseModel):
            bfabric_app_runner: str = "bfabric-app-runner==0.0.22"

        dependencies: Dependencies
        workunit_id: int
        app_yaml_path: str

        @classmethod
        def extract_workunit(cls, workunit: Workunit) -> WrapAppYamlTemplate.Params:
            # TODO this is not encodeable right now
            dependencies = cls.Dependencies()

            app_yaml_path = workunit.application.executable["program"]
            return cls(
                dependencies=dependencies,
                workunit_id=workunit.id,
                app_yaml_path=app_yaml_path,
            )

    def __init__(self, params: Params, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent / "wrap_app_yaml_template.bash.mako"

    def render_string(self) -> str:
        params = self._params.model_dump(mode="python")
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        return template.render(**params)
