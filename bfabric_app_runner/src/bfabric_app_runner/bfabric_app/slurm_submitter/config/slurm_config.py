from __future__ import annotations

from functools import cached_property

from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from bfabric_app_runner.specs.submitters_spec import SubmitterSlurmSpec  # noqa: TC001
from bfabric_app_runner.bfabric_app.slurm_submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,  # noqa: TC001
)  # noqa: TC001
from pydantic import BaseModel


class _SlurmConfigBase(BaseModel):
    submitter_config: SubmitterSlurmSpec
    app_version: AppVersion
    workunit_config: SlurmWorkunitParams


class SlurmConfig(_SlurmConfigBase):
    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        # TODO consistent naming (params vs config)
        merged = {**self.submitter_config.params, **self.app_version.submitter.params, **self.workunit_config.as_dict()}
        return {key: value for key, value in merged.items() if value is not None}

    def get_scratch_dir(self) -> str:
        # TODO check if cast is necessary later
        return str(self.submitter_config.config.worker_scratch_dir)
