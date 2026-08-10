from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, cast
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, field_validator

from bfabric.utils.path_safe_name import path_safe_name
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import (
    SlurmWorkunitParams,
)
from bfabric_app_runner.specs.app.app_spec import AppSpec
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit, interpolate_config_strings

if TYPE_CHECKING:
    from bfabric.entities import Workunit


class SlurmParameters(BaseModel):
    """The concrete Slurm parameters for a specific workunit.

    The three sources are merged in increasing order of precedence: ``submitter_params`` (this deployment's
    defaults), ``app_params`` (the app version), then ``workunit_params`` (what the user chose per submission).
    """

    submitter_params: dict[str, str | int | None]
    """Allows setting arbitrary parameters."""
    app_params: dict[str, str | int | None] = {}
    """The app version's ``submitter_params``; see :func:`_evaluate_app_params`."""
    job_script: Path
    """The path to store job script."""
    workunit_params: SlurmWorkunitParams
    """Allows setting a controlled set of parameters."""
    scratch_root: Path
    """The root directory for scratch space."""

    @cached_property
    def sbatch_params(self) -> dict[str, str]:
        merged = {**self.submitter_params, **self.app_params, **self.workunit_params.as_dict()}
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


def _evaluate_app_params(workunit: Workunit) -> dict[str, str | int | None]:
    """Returns the ``submitter_params`` of the app version this workunit will run, or ``{}`` if unavailable.

    This deliberately never raises: an unreadable or outdated app spec must not stop a workunit from being
    submitted, because the job itself reports app spec problems with far more context than the submitter can.
    """
    try:
        app_yaml = Path(workunit.application.executable["program"])
        app_spec = AppSpec.load_yaml(
            app_yaml=app_yaml,
            app_id=workunit.application.id,
            app_name=cast("str", workunit.application["name"]),
        )
        version = workunit.application_parameters.get("application_version")
        app_version = app_spec[version] if version is not None else None
        if app_version is None:
            logger.warning(f"App version {version!r} is not in {app_yaml}, ignoring app-level submitter params.")
            return {}
        return dict(app_version.submitter_params)
    except Exception:  # noqa: BLE001 -- intentionally broad: submitting the job matters more than these params
        logger.opt(exception=True).warning("Could not read app-level submitter params, using submitter defaults.")
        return {}


def evaluate_slurm_parameters(config_yaml_path: Path, workunit: Workunit) -> SlurmParameters:
    """Evaluates the Slurm Parameters from the YAML file for a given workunit."""
    config_file_template = _SlurmConfigFileTemplate.for_yaml(config_yaml_path)
    app_variables = VariablesApp(
        id=workunit.application.id, name=path_safe_name(cast("str", workunit.application["name"])), version="latest"
    )
    workunit_variables = VariablesWorkunit(id=workunit.id)
    config_file = config_file_template.evaluate(app=app_variables, workunit=workunit_variables)
    workunit_params = SlurmWorkunitParams.model_validate(workunit.submitter_parameters)
    return SlurmParameters(
        submitter_params=config_file.params,
        app_params=_evaluate_app_params(workunit),
        job_script=config_file.job_script,
        workunit_params=workunit_params,
        scratch_root=config_file.scratch_root,
    )
