from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, StringConstraints, field_validator

from bfabric_app_runner.specs.app.commands_spec import CommandsSpec
from bfabric_app_runner.specs.config_interpolation import interpolate_config_strings, VariablesApp

RESERVED_SBATCH_FLAGS = frozenset({"--chdir", "--error", "--export", "--output"})
"""Flags the submitter owns: they carry the job's logging, working directory and the environment the job body
relies on, so an app overriding one would break the job rather than just resize it."""

DURATION_SBATCH_FLAGS = frozenset({"--time", "--time-min"})
"""Flags whose SLURM format collides with YAML's sexagesimal integers, so they have to be quoted."""

_WORKUNIT_VARIABLE = re.compile(r"\$\{\s*workunit\b")


def _check_submitter_params(value: dict[str, str | int | None]) -> dict[str, str | int | None]:
    """Rejects flags the app spec may not set, and values that would be misread or would escape their line."""
    for flag, flag_value in value.items():
        if any(character in flag for character in "= \t"):
            raise ValueError(f"Invalid sbatch flag {flag!r}: a flag must not contain '=' or whitespace")
        if flag in RESERVED_SBATCH_FLAGS:
            raise ValueError(f"The flag {flag!r} is reserved by the submitter and cannot be set by an app")
        if flag in DURATION_SBATCH_FLAGS and isinstance(flag_value, int):
            raise ValueError(
                f"Quote the value of {flag!r}: YAML reads an unquoted 24:00:00 as the integer 86400, which sbatch "
                f"then reads as 86400 minutes"
            )
        if isinstance(flag_value, str) and _WORKUNIT_VARIABLE.search(flag_value):
            raise ValueError(
                f"The flag {flag!r} uses ${{workunit...}}, which is not available in an app spec; use ${{app...}}"
            )
        if isinstance(flag_value, str) and ("\n" in flag_value or "\r" in flag_value):
            # Each flag becomes one #SBATCH line, so a newline here would append lines to the generated job script.
            raise ValueError(f"The value of {flag!r} must be a single line")
    return value


SubmitterParams = Annotated[
    dict[Annotated[str, StringConstraints(pattern=r"^--")], str | int | None],
    AfterValidator(_check_submitter_params),
]


class AppVersion(BaseModel):
    """A concrete app version specification.

    For a better separation of concerns, the submitter will not be resolved automatically.
    """

    version: str = "latest"
    """Version identifier of this app version (e.g. ``"1.2.0"``)."""

    commands: CommandsSpec
    """The dispatch, process, and (optional) collect commands that implement this version."""

    submitter_params: SubmitterParams = {}
    """Extra ``sbatch`` flags for this version, e.g. ``{"--cpus-per-task": 24}``. They override the submitter's
    own defaults, and a ``null`` value removes a flag the submitter would otherwise pass."""


class AppVersionTemplate(BaseModel):
    """Template for a single app version, expanded to an ``AppVersion`` after variable interpolation."""

    version: str
    """Version identifier of this app version (e.g. ``"1.2.0"``)."""

    commands: CommandsSpec
    """The dispatch, process, and (optional) collect commands that implement this version."""

    submitter_params: SubmitterParams = {}
    """Extra ``sbatch`` flags for this version, e.g. ``{"--cpus-per-task": 24}``. They override the submitter's
    own defaults, and a ``null`` value removes a flag the submitter would otherwise pass."""

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

    submitter_params: SubmitterParams = {}
    """Extra ``sbatch`` flags shared by these versions, e.g. ``{"--cpus-per-task": 24}``. They override the
    submitter's own defaults, and a ``null`` value removes a flag the submitter would otherwise pass."""

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
