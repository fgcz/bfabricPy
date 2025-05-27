from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mako.template
from loguru import logger
from pydantic import BaseModel

from bfabric.utils.path_safe_name import path_safe_name

if TYPE_CHECKING:
    from bfabric.entities import Workunit


# TODO this is implementing the old yaml based logic for now, if there was enough time it should be app.zip spec instead
class AppRunnerWrapperTemplate:
    class Params(BaseModel):
        class Dependencies(BaseModel):
            bfabric_scripts: str = "bfabric-scripts==1.13.28"
            bfabric_app_runner: str = "bfabric-app-runner==0.0.22"

        dependencies: Dependencies
        working_directory: str
        workunit_id: int
        app_yaml_path: str

        @classmethod
        def extract_workunit(cls, workunit: Workunit) -> AppRunnerWrapperTemplate.Params:
            # TODO this is not encodeable right now
            dependencies = cls.Params.Dependencies()

            app_yaml_path = workunit.application["program"]
            # TODO hermetic isolation by B-Fabric instance!
            # TODO customizable
            # TODO this does not have the legacy logic of rediscovering existing folders
            app_name = path_safe_name(workunit.application["name"])
            app_id = workunit.application.id
            working_directory = f"/scratch/A{app_id}_{app_name}/WU{workunit.id}"

            return cls.Params(
                dependencies=dependencies,
                working_directory=working_directory,
                workunit_id=workunit.id,
                app_yaml_path=app_yaml_path,
            )

    def __init__(self, params: Params, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent / "app_runner_wrapper_template.bash.mako"

    def render_string(self) -> str:
        params = self._params.model_dump()
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        return template.render(**params)
