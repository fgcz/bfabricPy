import cyclopts

from bfabric_scripts.cli.cli_external_job import app as _app_external_job
from bfabric_scripts.cli.cli_read import app as _app_read

app = cyclopts.App()
app.command(_app_read, name="read")
app.command(_app_external_job, name="external-job")

if __name__ == "__main__":
    app()
