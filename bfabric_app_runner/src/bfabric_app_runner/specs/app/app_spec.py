from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

from bfabric_app_runner.specs.app.app_version import AppVersion, AppVersionMultiTemplate  # noqa: TCH001

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

    # TODO consider whether to reintroduce
    # bfabric: BfabricAppSpec
    versions: list[AppVersionMultiTemplate]

    def evaluate(self, app_id: str, app_name: str) -> AppSpec:
        """Evaluates the template to a concrete ``AppSpec`` instance."""
        versions_templates = [expanded for version in self.versions for expanded in version.expand_versions()]
        versions = [template.evaluate(app_id=app_id, app_name=app_name) for template in versions_templates]
        return AppSpec.model_validate({"versions": versions})


class AppSpec(BaseModel):
    """Parsed app versions from the app spec file."""

    versions: list[AppVersion]

    @classmethod
    def load_yaml(cls, app_yaml: Path, app_id: int | str, app_name: str) -> AppSpec:
        """Loads the app versions from the provided YAML file and evaluates the templates."""
        app_spec_file = AppSpecTemplate.model_validate(yaml.safe_load(app_yaml.read_text()))
        return app_spec_file.evaluate(app_id=str(app_id), app_name=str(app_name))

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
