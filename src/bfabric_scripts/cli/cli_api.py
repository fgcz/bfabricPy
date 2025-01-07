import cyclopts

from bfabric_scripts.cli.api.cli_api_log import cmd as _cmd_log
from bfabric_scripts.cli.api.cli_api_read import app as _cmd_read
from bfabric_scripts.cli.api.cli_api_save import app as _cmd_save

app = cyclopts.App()
app.command(_cmd_log, name="log")
app.command(_cmd_read, name="read")
app.command(_cmd_save, name="save")
