from __future__ import annotations
from pathlib import Path  # noqa: TC003
from functools import cached_property

from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit, interpolate_config_strings
from bfabric_app_runner.specs.submitters_spec import SubmitterSlurmSpec  # noqa: TC001
from bfabric_app_runner.simple_submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,  # noqa: TC001
)  # noqa: TC001
from pydantic import BaseModel


class _SlurmConfigBase(BaseModel):
    submitter_params: SubmitterSlurmSpec
    app_version: AppVersion
    workunit_params: SlurmWorkunitParams


class SlurmConfig(_SlurmConfigBase):
    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        merged = {**self.submitter_params.params, **self.app_version.submitter.params, **self.workunit_params.as_dict()}
        return {key: value for key, value in merged.items() if value is not None}

    def get_scratch_dir(self) -> Path:
        return self.submitter_params.config.worker_scratch_dir


class SlurmConfigTemplate(_SlurmConfigBase):
    def evaluate(self, app: VariablesApp, workunit: VariablesWorkunit) -> SlurmConfig:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data=data_template, variables={"app": app, "workunit": workunit})
        return SlurmConfig.model_validate(data)
