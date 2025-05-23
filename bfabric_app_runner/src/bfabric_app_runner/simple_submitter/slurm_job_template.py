from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import mako.template
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    import io


class Params(BaseModel):
    script: str
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
        params = self._params.model_dump()
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        target_file.write(template.render(**params))
