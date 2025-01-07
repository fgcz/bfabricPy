from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import yaml
from pydantic import BaseModel, field_validator

from app_runner.specs.app.commands_spec import CommandsSpec  # noqa: TCH001
from app_runner.specs.config_interpolation import interpolate_config_strings
from app_runner.specs.submitter_spec import SubmitterRef, SubmitterSpec  # noqa: TCH001

if TYPE_CHECKING:
    from pathlib import Path


class AppVersion(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterRef

    # TODO
    reuse_default_resource: bool = True

    def resolve_submitter(self, submitters: dict[str, SubmitterSpec], app_data: _SubstituteAppData) -> SubmitterSpec:
        if self.submitter.name not in submitters:
            raise ValueError(f"Submitter {self.submitter.name} not found in submitters.")
        submitter = self.submitter.resolve(submitters)
        submitter_data = submitter.model_dump(mode="json")
        submitter_data = interpolate_config_strings(submitter_data, variables={"app": app_data})
        return SubmitterSpec.model_validate(submitter_data)


@dataclass
class _SubstituteAppData:
    version: str
    id: str


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

        for version in self.version:
            version_data = self.model_dump(mode="json")
            version_data["version"] = version
            version_data = interpolate_config_strings(
                version_data, variables={"app": {"version": version, "id": app_id}}
            )
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
