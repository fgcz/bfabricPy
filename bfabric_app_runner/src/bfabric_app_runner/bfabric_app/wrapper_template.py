from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mako.template
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    import io
    from bfabric.experimental.workunit_definition import WorkunitDefinition
    from bfabric_app_runner.specs.app.app_version import AppVersion


class WrapperTemplateParams(BaseModel):
    app_version: AppVersion
    workunit_definition: WorkunitDefinition
    log_resource_id: int | None
    command: list[str]


class WrapperTemplate:
    def __init__(self, params: WrapperTemplateParams, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def for_params(cls, params: WrapperTemplateParams) -> WrapperTemplate:
        path = Path(__file__).parent / "wrapper_template.bash.mak"
        return cls(params=params, path=path)

    def render(self, target_file: io.TextIOBase) -> None:
        params = {
            "app_version": self._params.app_version.model_dump(mode="json"),
            "workunit_definition": self._params.workunit_definition.model_dump(mode="json"),
            "workunit_id": self._params.workunit_definition.registration.workunit_id,
            "log_resource_id": self._params.log_resource_id,
        }
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        target_file.write(template.render(**params))
