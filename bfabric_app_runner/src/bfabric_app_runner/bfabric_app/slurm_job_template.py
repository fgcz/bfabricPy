from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
import shlex
import mako.template
import yaml
from loguru import logger
from pydantic import BaseModel
from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from bfabric.experimental.workunit_definition import WorkunitDefinition  # noqa: TC002

if TYPE_CHECKING:
    import io


class Params(BaseModel):
    app_version: AppVersion
    workunit_definition: WorkunitDefinition
    working_directory: Path
    logging_resource_id: int | None
    command: list[str]
    sbatch_params: dict[str, str]


class SlurmJobTemplate:
    def __init__(self, params: Params, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def for_params(cls, **params: Any) -> SlurmJobTemplate:
        path = Path(__file__).parent / "wrapper_template.bash.mako"
        return cls(params=Params.model_validate(params), path=path)

    def render(self, target_file: io.TextIOBase) -> None:
        params = {
            "app_version_yml": yaml.safe_dump(self._params.app_version.model_dump(mode="json")),
            "workunit_definition_yml": yaml.safe_dump(self._params.workunit_definition.model_dump(mode="json")),
            "workunit_id": self._params.workunit_definition.registration.workunit_id,
            "working_directory": str(self._params.working_directory),
            "logging_resource_id": self._params.logging_resource_id,
            "command": shlex.join(self._params.command),
            "sbatch_params": self._params.sbatch_params,
        }
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        target_file.write(template.render(**params))
