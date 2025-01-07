from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import yaml
from mako.template import Template
from pydantic import BaseModel, field_validator

from app_runner.specs.app.commands_spec import CommandsSpec  # noqa: TCH001
from app_runner.specs.submitter_spec import SubmitterRef  # noqa: TCH001

if TYPE_CHECKING:
    from pathlib import Path


def _render_strings(data: Any, variables: dict[str, Any]) -> Any:
    """Recursively evaluates all strings in a data structure with Mako templates.

    This will not evaluate Mako templates in the YAML file itself, only in the individual strings.
    Since the current behavior is a subset of evaluating all strings in the YAML file, we could extend this later
    if it becomes necessary. However, it has the risk of making the config files more complex and should be avoided
    if possible.

    :param data: Any Python data structure (dict, list, str, etc.)
    :param variables: Dictionary of template variables and their values
    :return: The data structure with all strings evaluated
    """
    if isinstance(data, dict):
        return {key: _render_strings(value, variables) for key, value in data.items()}
    elif isinstance(data, list):
        return [_render_strings(item, variables) for item in data]
    elif isinstance(data, str):
        return str(Template(data).render(**variables))
    else:
        return data


class AppVersion(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterRef

    # TODO
    reuse_default_resource: bool = True


class AppVersionTemplate(BaseModel):
    version: list[str]
    commands: CommandsSpec
    submitter: SubmitterRef

    # TODO
    # Note: While we use the old submitter, this is still necessary
    reuse_default_resource: bool = True

    @field_validator("version", mode="before")
    def _version_ensure_list(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return [values]
        return values

    def expand(self, app_id: int | str) -> list[AppVersion]:
        versions = []

        @dataclass
        class AppData:
            version: str
            id: str

        for version in self.version:
            version_data = self.model_dump(mode="json")
            version_data["version"] = version
            version_data = _render_strings(version_data, variables={"app": AppData(version=version, id=str(app_id))})
            versions.append(AppVersion.model_validate(version_data))
        return versions


class AppVersionsTemplate(BaseModel):
    versions: list[AppVersionTemplate]


class AppVersions(BaseModel):
    versions: list[AppVersion]

    @classmethod
    def load_yaml(cls, path: Path, app_id: int | str) -> AppVersions:
        data = yaml.safe_load(path.read_text())
        model = AppVersionsTemplate.model_validate(data)
        versions = [expanded for version in model.versions for expanded in version.expand(app_id=app_id)]
        return AppVersions.model_validate({"versions": versions})

    @property
    def available_versions(self) -> set[str]:
        return {version.version for version in self.versions}

    def __getitem__(self, version: str) -> AppVersion | None:
        for app_version in self.versions:
            if app_version.version == version:
                return app_version
        return None
