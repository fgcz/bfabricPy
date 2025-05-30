from __future__ import annotations

from functools import cached_property
from pathlib import Path  # noqa: TC003

import yaml
from pydantic import BaseModel

from bfabric.entities import Workunit  # noqa: TC002
from bfabric.utils.path_safe_name import path_safe_name
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,  # noqa: TC001
)  # noqa: TC001
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit, interpolate_config_strings


class _SlurmParametersBase(BaseModel):
    # Note: Originally, the idea was that at the app level app_params could also be defined, but this was omitted for
    #       simplicity in this version.
    submitter_params: dict[str, str | int | None]
    """Allows setting arbitrary parameters."""
    workunit_params: SlurmWorkunitParams
    """Allows setting a controlled set of parameters."""


class SlurmParameters(_SlurmParametersBase):
    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        merged = {**self.submitter_params, **self.workunit_params.as_dict()}
        return {key: str(value) for key, value in merged.items() if value is not None}


class SlurmParametersTemplate(_SlurmParametersBase):
    def evaluate(self, app: VariablesApp, workunit: VariablesWorkunit) -> SlurmParameters:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data=data_template, variables={"app": app, "workunit": workunit})
        return SlurmParameters.model_validate(data)

    @classmethod
    def for_yaml_and_workunit(cls, config_yaml_path: Path, workunit: Workunit) -> SlurmParametersTemplate:
        submitter_params = yaml.safe_load(config_yaml_path.read_text())["params"]
        workunit_params = SlurmWorkunitParams.model_validate(workunit.submitter_parameters)
        return SlurmParametersTemplate(submitter_params=submitter_params, workunit_params=workunit_params)


def evaluate_slurm_parameters(config_yaml_path: Path, workunit: Workunit) -> SlurmParameters:
    """Evaluates the Slurm Parameters from the YAML file for a given workunit."""
    config_template = SlurmParametersTemplate.for_yaml_and_workunit(config_yaml_path, workunit)
    app_variables = VariablesApp(
        id=workunit.application.id, name=path_safe_name(workunit.application["name"]), version="latest"
    )
    workunit_variables = VariablesWorkunit(id=workunit.id)
    return config_template.evaluate(app=app_variables, workunit=workunit_variables)
