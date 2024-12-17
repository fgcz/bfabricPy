import cyclopts

from bfabric_scripts.cli.api.cli_api_log import cmd as _cmd_log
from bfabric_scripts.cli.api.cli_api_read import app as _cmd_read

app = cyclopts.App()
app.command(_cmd_log, name="log")
app.command(_cmd_read, name="read")
