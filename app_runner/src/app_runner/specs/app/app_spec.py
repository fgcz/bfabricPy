from __future__ import annotations

from typing import Any, TYPE_CHECKING

import yaml
from pydantic import BaseModel, field_validator

from app_runner.specs import config_interpolation
from app_runner.specs.app.commands_spec import CommandsSpec  # noqa: TCH001
from app_runner.specs.config_interpolation import interpolate_config_strings
from app_runner.specs.submitter_spec import SubmitterRef, SubmitterSpec, SubmittersSpec  # noqa: TCH001

if TYPE_CHECKING:
    from pathlib import Path


class AppVersion(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterSpec
    # TODO
    reuse_default_resource: bool = True


class AppVersionTemplate(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterRef
    # TODO
    reuse_default_resource: bool = True

    def resolve(self, submitters: dict[str, SubmitterSpec], app_id: str, app_name: str) -> AppVersion:
        if self.submitter.name not in submitters:
            raise ValueError(f"Submitter {self.submitter.name} not found in submitters.")
        variables_app = config_interpolation.VariablesApp(id=app_id, name=app_name, version=self.version)

        data_template = self.model_dump(mode="json")
        data_template["submitter"] = self.submitter.resolve(submitters).model_dump(mode="json")
        data = interpolate_config_strings(data_template, variables={"app": variables_app})

        return AppVersion.model_validate(data)


class AppVersionMultiTemplate(BaseModel):
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

    def expand(self) -> list[AppVersionTemplate]:
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


class BfabricAppSpec(BaseModel):
    """Contains the app specification information that is relevant to bfabric..."""

    app_runner: str


class AppSpecFile(BaseModel):
    bfabric: BfabricAppSpec
    versions: list[AppVersionMultiTemplate]

    def expand(self) -> AppSpecTemplates:
        return AppSpecTemplates.model_validate(
            {
                "bfabric": self.bfabric,
                "versions": [expanded for version in self.versions for expanded in version.expand()],
            }
        )


class AppSpecTemplates(BaseModel):
    bfabric: BfabricAppSpec
    versions: list[AppVersionTemplate]

    def resolve(self, submitters: dict[str, SubmitterSpec], app_id: str, app_name: str) -> AppVersions:
        return AppVersions.model_validate(
            {
                "versions": [
                    version.resolve(submitters=submitters, app_id=app_id, app_name=app_name)
                    for version in self.versions
                ]
            }
        )


class ResolvedAppVersion(BaseModel):
    version: str
    commands: CommandsSpec
    submitter: SubmitterSpec
    # TODO
    reuse_default_resource: bool = True


class AppVersions(BaseModel):
    versions: list[AppVersion]

    @classmethod
    def load_yaml(cls, app_yaml: Path, submitters_yaml: Path, app_id: int | str, app_name: str) -> AppVersions:
        app_spec_file = AppSpecFile.model_validate(yaml.safe_load(app_yaml.read_text()))
        submitters = SubmittersSpec.model_validate(yaml.safe_load(submitters_yaml.read_text()))
        x = app_spec_file.expand()
        x = x.resolve(submitters=submitters.submitters, app_id=str(app_id), app_name=str(app_name))
        return x

    @property
    def available_versions(self) -> set[str]:
        return {version.version for version in self.versions}

    def resolve_version(
        self, version: str, submitters: dict[str, SubmitterSpec], variables: dict[str, Any]
    ) -> ResolvedAppVersion:
        app_version = self[version]
        if app_version is None:
            raise ValueError(f"Version {version} not found in app versions.")
        return ResolvedAppVersion(
            version=app_version.version,
            commands=app_version.commands,
            submitter=app_version.resolve_submitter(submitters=submitters, variables=variables),
            reuse_default_resource=app_version.reuse_default_resource,
        )

    def __getitem__(self, version: str) -> AppVersion | None:
        for app_version in self.versions:
            if app_version.version == version:
                return app_version
        return None
