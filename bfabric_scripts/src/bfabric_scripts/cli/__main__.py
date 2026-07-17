import importlib.metadata

import cyclopts

from bfabric.utils.cli_integration import setup_script_logging
from bfabric_scripts.cli.cli_api import cmd_api
from bfabric_scripts.cli.cli_dataset import cmd_dataset
from bfabric_scripts.cli.cli_executable import cmd_executable
from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_feeder import cmd_feeder
from bfabric_scripts.cli.cli_auth import cmd_auth
from bfabric_scripts.cli.cli_workunit import cmd_workunit

package_version = importlib.metadata.version("bfabric_scripts")

app = cyclopts.App(version=package_version)
_ = app.command(cmd_api, name="api")
_ = app.command(cmd_dataset, name="dataset")
_ = app.command(cmd_executable, name="executable")
_ = app.command(cmd_workunit, name="workunit")
_ = app.command(cmd_feeder, name="feeder")
_ = app.command(cmd_auth, name="auth")

# TODO delete after transitory release
_ = app.command(_app_external_job, name="external-job")


def main() -> None:
    """CLI entry point: configure logging once, then dispatch.

    Commands using ``@use_client`` set logging up themselves, but those that don't (e.g. ``auth``)
    would otherwise run under loguru's default DEBUG handler. Setting up here covers every command;
    the per-command call is idempotent.
    """
    setup_script_logging()
    app()


if __name__ == "__main__":
    main()
