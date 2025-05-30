"""This module defines some CLI operations without a script, but rather used by directly importing the module."""

import re
from pathlib import Path

import cyclopts
import yaml

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.specs.app.app_spec import BfabricAppSpec

app = cyclopts.App(help="Bfabric app runner integration API commands.")


@app.command
@use_client
def report_workunit_failed(workunit_id: int, *, client: Bfabric) -> None:
    """Sets the status of a workunit to 'failed'."""
    client.save("workunit", {"id": workunit_id, "status": "failed"})


@app.command
@use_client
def report_workunit_available(workunit_id: int, *, client: Bfabric) -> None:
    """Sets the status of a workunit to 'successful'."""
    client.save("workunit", {"id": workunit_id, "status": "available"})


@app.command
def read_app_yaml_app_runner_dependency(path: Path) -> None:
    """Read uv-compatible dependency specifier from app yaml."""
    # NOTE: This is not super robust, but AppSpec forcing Bfabric into the app spec instead of app version
    #       is a bit inconsistent and obsolete with app.zip.
    config = BfabricAppSpec.model_validate(yaml.safe_load(path.read_text())["bfabric"])
    if re.match(r"^\d+\.\d+\.\d+$", config.app_runner_version):
        print(f"bfabric-app-runner=={config.app_runner_version}")
    else:
        print(f"bfabric-app-runner@{config.app_runner_version}")


if __name__ == "__main__":
    app()
