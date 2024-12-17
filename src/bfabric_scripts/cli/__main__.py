import cyclopts

from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_read import app as _app_read
from bfabric_scripts.cli.cli_workunit import app as _app_workunit
from bfabric_scripts.cli.cli_api import app as _app_api

app = cyclopts.App()
app.command(_app_read, name="read")
app.command(_app_external_job, name="external-job")
app.command(_app_workunit, name="workunit")
app.command(_app_api, name="api")

if __name__ == "__main__":
    app()
