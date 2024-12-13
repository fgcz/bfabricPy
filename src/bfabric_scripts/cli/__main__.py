import cyclopts

from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_read import app as _app_read
from bfabric_scripts.cli.cli_workunit import app as _app_workunit

app = cyclopts.App()
app.command(_app_read, name="read")
app.command(_app_external_job, name="external-job")
app.command(_app_workunit, name="workunit")

if __name__ == "__main__":
    app()
