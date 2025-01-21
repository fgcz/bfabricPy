from __future__ import annotations

from functools import cached_property

from pydantic import BaseModel

from app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from app_runner.specs.submitters_spec import SubmitterSlurmSpec  # noqa: TC001
from app_runner.submitter.config.slurm_workunit_params import SlurmWorkunitParams  # noqa: TC001


class _SlurmConfigBase(BaseModel):
    submitter_config: SubmitterSlurmSpec
    app_version: AppVersion
    workunit_config: SlurmWorkunitParams


class SlurmConfig(_SlurmConfigBase):
    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        # TODO consistent naming (params vs config)
        merged = {**self.submitter_config.params, **self.app_version, **self.workunit_config.as_dict()}
        return {key: value for key, value in merged.items() if value is not None}

    # @property
    # def get_scratch_dir(self) -> str:
    #    # TODO ensure it's a str
    #    return self._submitter_config.config.worker_scratch_dir
