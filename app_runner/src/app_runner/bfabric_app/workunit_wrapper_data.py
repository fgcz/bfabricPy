from __future__ import annotations

from pydantic import BaseModel

from app_runner.specs.app.app_spec import AppSpecTemplate  # noqa: TC001
from bfabric.experimental.workunit_definition import WorkunitDefinition  # noqa: TC002


class WorkunitWrapperData(BaseModel):
    # TODO this could be revisited in the future, e.g. whether we want to merge this part into the app_definition
    # TODO should the template be substituted already?
    workunit: WorkunitDefinition
    app: AppSpecTemplate
