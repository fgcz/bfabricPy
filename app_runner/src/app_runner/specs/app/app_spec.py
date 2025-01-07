from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import yaml
from mako.template import Template
from pydantic import BaseModel, field_validator

from app_runner.specs.app.commands_spec import CommandsSpec  # noqa: TCH001

if TYPE_CHECKING:
    from pathlib import Path


def substitute_strings(data: Any, substitutions: dict[str, str]) -> Any:
    """Recursively substitutes template variables in a data structure.
    TODO docstring

    Args:
        data: Any Python data structure (dict, list, str, etc.)
        substitutions: Dictionary of template variables and their values

    Returns:
        Data structure with all template strings substituted
    """
    if isinstance(data, dict):
        return {key: substitute_strings(value, substitutions) for key, value in data.items()}
    elif isinstance(data, list):
        return [substitute_strings(item, substitutions) for item in data]
    elif isinstance(data, str):
        return str(Template(data).render(**substitutions))
    else:
        return data


# Gclass AppVersion(BaseModel):
#    # TODO test both cases
#    version: list[str]
#    commands: CommandsSpec
#    # TODO
#    # Note: While we use the old submitter, this is still necessary
#    reuse_default_resource: bool = True
#
#    @field_validator("version", mode="before")
#    def _version_ensure_list(cls, values):
#        if not isinstance(values, list):
#            return [values]
#        return values
#
#
# class AppSpec(BaseModel):
#    versions: dict[str, AppVersion]
#
#
# class AppSpecResolved(BaseModel):
#    pass


class AppVersion(BaseModel):
    version: str
    commands: CommandsSpec
    # TODO
    reuse_default_resource: bool = True


class AppVersionTemplate(BaseModel):
    version: list[str]
    commands: CommandsSpec
    # TODO
    # Note: While we use the old submitter, this is still necessary
    reuse_default_resource: bool = True

    @field_validator("version", mode="before")
    def _version_ensure_list(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return [values]
        return values

    def expand(self) -> list[AppVersion]:
        versions = []

        @dataclass
        class AppData:
            version: str

        for version in self.version:
            version_data = self.model_dump(mode="json")
            version_data["version"] = version
            version_data = substitute_strings(version_data, substitutions={"app": AppData(version)})
            versions.append(AppVersion.model_validate(version_data))
        return versions


class AppVersionsTemplate(BaseModel):
    versions: list[AppVersionTemplate]


class AppVersions(BaseModel):
    versions: list[AppVersion]

    @classmethod
    def load_yaml(cls, path: Path) -> AppVersions:
        data = yaml.safe_load(path.read_text())
        model = AppVersionsTemplate.model_validate(data)
        # versions = itertools.chain.from_iterable(version.expand() for version in model.versions)
        versions = [expanded for version in model.versions for expanded in version.expand()]
        return AppVersions.model_validate({"versions": versions})

    @property
    def available_versions(self) -> set[str]:
        return set(version.version for version in self.versions)

    def __getitem__(self, version: str) -> AppVersion | None:
        for app_version in self.versions:
            if app_version.version == version:
                return app_version
        return None
