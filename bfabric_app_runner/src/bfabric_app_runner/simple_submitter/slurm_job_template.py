from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mako.template
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    from bfabric.entities import Workunit


class SlurmJobTemplate:
    class Params(BaseModel):
        sbatch_params: dict[str, str]

        @classmethod
        def extract_workunit(cls, workunit: Workunit) -> SlurmJobTemplate.Params:
            return cls.Params(sbatch_params=workunit.submitter_parameters)

    def __init__(self, params: Params, wrapped_script: str, path: Path) -> None:
        self._params = params
        self._wrapped_script = wrapped_script
        self._path = path

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent / "slurm_job_template.bash.mako"

    def render_string(self) -> str:
        params = self._params.model_dump()
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        return template.render(**params, wrapped_script=self._wrapped_script)
