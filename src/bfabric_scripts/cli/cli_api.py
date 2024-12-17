import cyclopts

from bfabric_scripts.cli.api.cli_api_log import cmd as _cmd_log

app = cyclopts.App()
app.command(_cmd_log, name="log")
