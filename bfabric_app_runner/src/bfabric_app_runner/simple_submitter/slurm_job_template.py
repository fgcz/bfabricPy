from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any

import mako.template
from loguru import logger
from pydantic import BaseModel

from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001

if TYPE_CHECKING:
    import io


class Params(BaseModel):
    app_version: AppVersion
    command: list[str]
    sbatch_params: dict[str, str]


class SlurmJobTemplate:
    def __init__(self, params: Params, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def for_params(cls, **params: Any) -> SlurmJobTemplate:
        path = Path(__file__).parent / "slurm_job_template.bash.mako"
        return cls(params=Params.model_validate(params), path=path)

    def render(self, target_file: io.TextIOBase) -> None:
        params = {
            "command": shlex.join(self._params.command),
            "sbatch_params": self._params.sbatch_params,
        }
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        target_file.write(template.render(**params))
