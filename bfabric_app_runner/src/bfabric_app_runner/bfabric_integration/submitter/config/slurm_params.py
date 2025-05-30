from __future__ import annotations

from functools import cached_property
from pathlib import Path  # noqa: TC003

import yaml
from pydantic import BaseModel, field_validator

from bfabric.entities import Workunit  # noqa: TC002
from bfabric.utils.path_safe_name import path_safe_name
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,  # noqa: TC001
)  # noqa: TC001
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit, interpolate_config_strings


class SlurmParameters(BaseModel):
    """The concrete Slurm parameters for a specific workunit."""

    # Note: Originally, the idea was that at the app level app_params could also be defined, but this was omitted for
    #       simplicity in this version.
    submitter_params: dict[str, str | int | None]
    """Allows setting arbitrary parameters."""
    job_script: Path
    """The path to store job script."""
    workunit_params: SlurmWorkunitParams
    """Allows setting a controlled set of parameters."""
    scratch_root: Path
    """The root directory for scratch space."""

    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        merged = {**self.submitter_params, **self.workunit_params.as_dict()}
        return {key: str(value) for key, value in merged.items() if value is not None}


class _SlurmConfigFile(BaseModel):
    params: dict[str, str | int | None]
    job_script: Path
    scratch_root: Path

    @field_validator("job_script", "scratch_root", mode="after")
    @classmethod
    def expand_user_in_paths(cls, value: Path) -> Path:
        """Expands user in paths."""
        return value.expanduser()


class _SlurmConfigFileTemplate(BaseModel):
    """The generic slurm configuration file, with template strings not yet evaluated."""

    params: dict[str, str | int | None]
    job_script: str
    scratch_root: Path

    @classmethod
    def for_yaml(cls, path: Path) -> _SlurmConfigFileTemplate:
        return _SlurmConfigFileTemplate.model_validate(yaml.safe_load(path.read_text()))

    def evaluate(self, app: VariablesApp, workunit: VariablesWorkunit) -> _SlurmConfigFile:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data=data_template, variables={"app": app, "workunit": workunit})
        return _SlurmConfigFile.model_validate(data)


def evaluate_slurm_parameters(config_yaml_path: Path, workunit: Workunit) -> SlurmParameters:
    """Evaluates the Slurm Parameters from the YAML file for a given workunit."""
    config_file_template = _SlurmConfigFileTemplate.for_yaml(config_yaml_path)
    app_variables = VariablesApp(
        id=workunit.application.id, name=path_safe_name(workunit.application["name"]), version="latest"
    )
    workunit_variables = VariablesWorkunit(id=workunit.id)
    config_file = config_file_template.evaluate(app=app_variables, workunit=workunit_variables)
    workunit_params = SlurmWorkunitParams.model_validate(workunit.submitter_parameters)
    return SlurmParameters(
        submitter_params=config_file.params,
        job_script=config_file.job_script,
        workunit_params=workunit_params,
        scratch_root=config_file.scratch_root,
    )
