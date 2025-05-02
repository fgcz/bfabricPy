from __future__ import annotations

from typing import TYPE_CHECKING
from collections import Counter

import yaml
from pydantic import BaseModel, field_validator

from bfabric_app_runner.specs.app.app_version import AppVersion, AppVersionMultiTemplate  # noqa: TCH001
from bfabric_app_runner.specs.config_interpolation import VariablesApp

if TYPE_CHECKING:
    from pathlib import Path


class BfabricAppSpec(BaseModel):
    """Contains the app specification information that is relevant to bfabric, and not exactly the app itself."""

    app_runner: str
    """Specifies the app runner version to use for the app.

    We support both a PyPI version (e.g. `0.0.17`) as well as a git reference, which is a string in the
    format `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_app_runner` where you can specify
    any git reference instead of `main` as needed.
    """


class AppSpecTemplate(BaseModel):
    """This model defines the app_spec definition in a file.

    As the name suggests, this is a template that can be expanded to a concrete ``AppSpec`` instance.
    The main difference is that this may contain usages of `Variables`. TODO
    """

    bfabric: BfabricAppSpec
    versions: list[AppVersionMultiTemplate]

    # TODO this should take the variables as param instead
    def evaluate(self, app_id: int, app_name: str) -> AppSpec:
        """Evaluates the template to a concrete ``AppSpec`` instance."""
        version_templates = [expanded for version in self.versions for expanded in version.expand_versions()]
        versions = []
        for version_template in version_templates:
            variables_app = VariablesApp(id=app_id, name=app_name, version=version_template.version)
            versions.append(version_template.evaluate(variables_app=variables_app))
        # TODO add interpolation for bfabric config for consistency
        return AppSpec.model_validate({"versions": versions, "bfabric": self.bfabric})


class AppSpec(BaseModel):
    """Parsed app versions from the app spec file."""

    bfabric: BfabricAppSpec
    versions: list[AppVersion]

    @field_validator("versions", mode="after")
    def no_duplicate_versions(cls, values: list[AppVersion]) -> list[AppVersion]:
        """Validates that there are no duplicate versions in the app spec."""
        counts = Counter([v.version for v in values])
        duplicates = [version for version, count in counts.items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate versions found: {duplicates}")
        return values

    @classmethod
    def load_yaml(cls, app_yaml: Path, app_id: int | str, app_name: str) -> AppSpec:
        """Loads the app versions from the provided YAML file and evaluates the templates."""
        app_spec_file = AppSpecTemplate.model_validate(yaml.safe_load(app_yaml.read_text()))
        return app_spec_file.evaluate(app_id=int(app_id), app_name=str(app_name))

    @property
    def available_versions(self) -> set[str]:
        """The available versions of the app."""
        return {version.version for version in self.versions}

    def __contains__(self, version: str) -> bool:
        return version in self.available_versions

    def __getitem__(self, version: str) -> AppVersion | None:
        """Returns the app version with the provided version number or None if it does not exist."""
        for app_version in self.versions:
            if app_version.version == version:
                return app_version
        return None
