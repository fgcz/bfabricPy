from __future__ import annotations

from functools import cached_property

from pydantic import BaseModel

from app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from app_runner.specs.submitters_spec import SubmitterSlurmSpec  # noqa: TC001
from app_runner.submitter.slurm_submitter_workunit_params import SlurmSubmitterWorkunitParams  # noqa: TC001


class SlurmSubmitterParams(BaseModel):
    submitter_config: SubmitterSlurmSpec
    app_version: AppVersion
    workunit_config: SlurmSubmitterWorkunitParams

    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        """The params that should be passed to the sbatch command."""
        # TODO consistent naming (params vs config)
        merged = {**self.submitter_config.params, **self.app_version, **self.workunit_config.as_dict()}
        return {key: value for key, value in merged.items() if value is not None}

    @property
    def get_scratch_dir(self) -> str:
        # TODO ensure it's a str
        return self._submitter_config.config.worker_scratch_dir
