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
        workunit_id: int
        app_yaml_path: str
        scratch_root: Path

        @classmethod
        def extract_workunit(cls, workunit: Workunit, scratch_root: Path) -> WrapAppYamlTemplate.Params:
            app_yaml_path = workunit.application.executable["program"]
            return cls(
                workunit_id=workunit.id,
                app_yaml_path=app_yaml_path,
                scratch_root=scratch_root,
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
