from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

from bfabric_app_runner.specs.app.commands_spec import CommandsSpec
from bfabric_app_runner.specs.config_interpolation import interpolate_config_strings, VariablesApp


class AppVersion(BaseModel):
    """A concrete app version specification.

    For a better separation of concerns, the submitter will not be resolved automatically.
    """

    version: str = "latest"
    """Version identifier of this app version (e.g. ``"1.2.0"``)."""

    commands: CommandsSpec
    """The dispatch, process, and (optional) collect commands that implement this version."""

    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True
    """Legacy flag: reuse the workunit's auto-created default resource for the first copied output
    instead of creating a new resource entry."""


class AppVersionTemplate(BaseModel):
    """Template for a single app version, expanded to an ``AppVersion`` after variable interpolation."""

    version: str
    """Version identifier of this app version (e.g. ``"1.2.0"``)."""

    commands: CommandsSpec
    """The dispatch, process, and (optional) collect commands that implement this version."""

    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True
    """Legacy flag: reuse the workunit's auto-created default resource for the first copied output
    instead of creating a new resource entry."""

    def evaluate(self, variables_app: VariablesApp) -> AppVersion:
        """Evaluates the template to a concrete ``AppVersion`` instance."""
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data_template, variables={"app": variables_app, "workunit": None})
        return AppVersion.model_validate(data)


class AppVersionMultiTemplate(BaseModel):
    """App version template that may declare several version strings sharing the same commands.

    A single version string is also accepted and normalized to a one-element list.
    """

    version: list[str]
    """Version identifiers that share this definition; a single string is coerced to a one-element list."""

    commands: CommandsSpec
    """The dispatch, process, and (optional) collect commands that implement these versions."""

    # TODO remove when new submitter becomes available
    reuse_default_resource: bool = True
    """Legacy flag: reuse the workunit's auto-created default resource for the first copied output
    instead of creating a new resource entry."""

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
