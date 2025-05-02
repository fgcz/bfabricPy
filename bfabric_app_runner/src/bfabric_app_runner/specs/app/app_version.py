from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

from bfabric_app_runner.specs.app.commands_spec import CommandsSpec  # noqa: TCH001
from bfabric_app_runner.specs.config_interpolation import interpolate_config_strings, VariablesApp
from bfabric_app_runner.specs.submitter_ref import SubmitterRef  # noqa: TCH001


class AppVersion(BaseModel):
    """A concrete app version specification.

    For a better separation of concerns, the submitter will not be resolved automatically.
    """

    version: str = "latest"
    commands: CommandsSpec
    submitter: SubmitterRef
    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True


class AppVersionTemplate(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterRef
    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True

    def evaluate(self, variables_app: VariablesApp) -> AppVersion:
        """Evaluates the template to a concrete ``AppVersion`` instance."""
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data_template, variables={"app": variables_app, "workunit": None})
        return AppVersion.model_validate(data)


class AppVersionMultiTemplate(BaseModel):
    version: list[str]
    commands: CommandsSpec
    submitter: SubmitterRef

    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True

    @field_validator("version", mode="before")
    def _version_ensure_list(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return [values]
        return values

    def expand_versions(self) -> list[AppVersionTemplate]:
        """Returns a list of individual ``AppVersionTemplate`` instances, expanding each template of multiple versions.
        If substitutions are used they will not be expanded yet but rather when converting the template to a concrete
        AppVersion.
        """
        versions = []
        for version in self.version:
            version_data = self.model_dump(mode="json")
            version_data["version"] = version
            versions.append(AppVersionTemplate.model_validate(version_data))
        return versions
