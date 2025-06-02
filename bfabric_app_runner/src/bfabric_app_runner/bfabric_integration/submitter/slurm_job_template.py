from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mako.template
from loguru import logger

if TYPE_CHECKING:
    from bfabric_app_runner.bfabric_integration.submitter.config.slurm_params import SlurmParameters


class SlurmJobTemplate:
    def __init__(self, params: SlurmParameters, workunit_id: int, wrapped_script: str, path: Path) -> None:
        self._params = params
        self._workunit_id = workunit_id
        self._wrapped_script = wrapped_script
        self._path = path

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent / "slurm_job_template.bash.mako"

    def render_string(self) -> str:
        params = {
            "sbatch_params": self._params.sbatch_params,
            "wrapped_script": self._wrapped_script,
            "workunit_id": self._workunit_id,
        }
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        return template.render(**params)
