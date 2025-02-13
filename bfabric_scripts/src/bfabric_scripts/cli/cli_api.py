import cyclopts

from bfabric_scripts.cli.api.cli_api_create import app as _cmd_create
from bfabric_scripts.cli.api.cli_api_delete import app as _cmd_delete
from bfabric_scripts.cli.api.cli_api_log import cmd as _cmd_log
from bfabric_scripts.cli.api.cli_api_read import app as _cmd_read
from bfabric_scripts.cli.api.cli_api_save import app as _cmd_save
from bfabric_scripts.cli.api.cli_api_update import app as _cmd_update

app = cyclopts.App()
app.command(_cmd_create, name="create")
app.command(_cmd_delete, name="delete")
app.command(_cmd_read, name="read")
app.command(_cmd_update, name="update")

# TODO delete or move
app.command(_cmd_log, name="log")
# TODO delete
app.command(_cmd_save, name="save")
