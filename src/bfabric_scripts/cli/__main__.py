import cyclopts

from bfabric_scripts.cli.cli_api import app as _app_api
from bfabric_scripts.cli.cli_executable import app as _app_executable
from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_workunit import app as _app_workunit

app = cyclopts.App()
app.command(_app_external_job, name="external-job")
app.command(_app_workunit, name="workunit")
app.command(_app_api, name="api")
app.command(_app_executable, name="executable")

if __name__ == "__main__":
    app()
