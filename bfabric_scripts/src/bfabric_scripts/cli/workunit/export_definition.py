from pathlib import Path

import yaml

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client


@use_client
def cmd_workunit_export_definition(workunit_id: int, target_path: Path | None = None, *, client: Bfabric) -> None:
    """Exports a workunit_definition.yml file for the specified workunit.

    :param workunit_id: the workunit ID
    :param target_path: the target path for the workunit_definition.yml file (default: workunit_definition.yml)
    """
    target_path = target_path if target_path is not None else Path("workunit_definition.yml")
    workunit_definition = WorkunitDefinition.from_ref(workunit_id, client=client)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = workunit_definition.model_dump(mode="json")
    target_path.write_text(yaml.safe_dump(data))
