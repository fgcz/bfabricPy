from pathlib import Path
from loguru import logger
import yaml

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.utils.cli_integration import use_client


@use_client
def cmd_workunit_export_resources(workunit_id: int, target_path: Path | None = None, *, client: Bfabric):
    # filename handling
    target_path = Path(f"workunit_{workunit_id}_resources.yml") if target_path is None else target_path
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # find the workunit
    workunit = Workunit.find(id=workunit_id, client=client)

    # generate the yaml content
    data = {
        "inputs": [{"type": "bfabric_resource", "id": resource_id} for resource_id in sorted(workunit.resources.ids)]
    }
    target_path.write_text(yaml.safe_dump(data))
    logger.success(f"Exported {target_path}")
