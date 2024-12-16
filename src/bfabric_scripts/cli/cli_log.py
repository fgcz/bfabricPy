import cyclopts

from bfabric_scripts.cli.log.log_write import cmd as _cmd_log_write

# TODO one thing to consider before this is fully ready is maybe it should be merged into the external-job command
#      which currently already contains a lot of system functionality

app = cyclopts.App()
app.command(_cmd_log_write, name="write")
