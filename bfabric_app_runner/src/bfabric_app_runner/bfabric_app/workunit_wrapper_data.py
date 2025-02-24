from __future__ import annotations

from bfabric.experimental.workunit_definition import WorkunitDefinition  # noqa: TC002
from bfabric_app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from pydantic import BaseModel


class WorkunitWrapperData(BaseModel):
    workunit_definition: WorkunitDefinition
    app_version: AppVersion
    app_runner_version: str
