import cyclopts

from bfabric_scripts.cli.api._deprecated_log import cmd as _cmd_log
from bfabric_scripts.cli.api.create import cmd_api_create
from bfabric_scripts.cli.api.delete import cmd_api_delete
from bfabric_scripts.cli.api.read import cmd_api_read
from bfabric_scripts.cli.api.update import cmd_api_update

cmd_api = cyclopts.App(help="Commands for interacting with B-Fabric API directly.")
cmd_api.command(cmd_api_create, name="create")
cmd_api.command(cmd_api_delete, name="delete")
cmd_api.command(cmd_api_read, name="read")
cmd_api.command(cmd_api_update, name="update")

# TODO delete after transitory release
cmd_api.command(_cmd_log, name="log")
