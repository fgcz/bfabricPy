import importlib.metadata

import cyclopts

from bfabric_scripts.cli.cli_api import cmd_api
from bfabric_scripts.cli.cli_dataset import cmd_dataset
from bfabric_scripts.cli.cli_executable import cmd_executable
from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_workunit import cmd_workunit

package_version = importlib.metadata.version("bfabric_scripts")

app = cyclopts.App(version=package_version)
app.command(cmd_api, name="api")
app.command(cmd_dataset, name="dataset")
app.command(cmd_executable, name="executable")
app.command(cmd_workunit, name="workunit")

# TODO delete after transitory release
app.command(_app_external_job, name="external-job")

if __name__ == "__main__":
    app()
