from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

from app_runner.specs.app.app_version import AppVersion, AppVersionTemplate, AppVersionMultiTemplate  # noqa: TCH001

if TYPE_CHECKING:
    from pathlib import Path


class BfabricAppSpec(BaseModel):
    """Contains the app specification information that is relevant to bfabric..."""

    # TODO unclear if it should be kept
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

    def resolve(self, app_id: str, app_name: str) -> AppVersions:
        return AppVersions.model_validate(
            {"versions": [version.evaluate(app_id=app_id, app_name=app_name) for version in self.versions]}
        )


class AppVersions(BaseModel):
    versions: list[AppVersion]

    @classmethod
    def load_yaml(cls, app_yaml: Path, app_id: int | str, app_name: str) -> AppVersions:
        app_spec_file = AppSpecFile.model_validate(yaml.safe_load(app_yaml.read_text()))
        x = app_spec_file.expand()
        x = x.resolve(app_id=str(app_id), app_name=str(app_name))
        return x

    @property
    def available_versions(self) -> set[str]:
        return {version.version for version in self.versions}

    def __getitem__(self, version: str) -> AppVersion | None:
        for app_version in self.versions:
            if app_version.version == version:
                return app_version
        return None
