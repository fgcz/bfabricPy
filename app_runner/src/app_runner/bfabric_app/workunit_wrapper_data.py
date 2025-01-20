from __future__ import annotations

from pydantic import BaseModel

from app_runner.specs.app.app_version import AppVersion  # noqa: TC001
from bfabric.experimental.workunit_definition import WorkunitDefinition  # noqa: TC002


class WorkunitWrapperData(BaseModel):
    workunit_definition: WorkunitDefinition
    app_version: AppVersion
