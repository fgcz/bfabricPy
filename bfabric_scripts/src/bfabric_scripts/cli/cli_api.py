import cyclopts

from bfabric_scripts.cli.api.create import cmd_api_create
from bfabric_scripts.cli.api.delete import cmd_api_delete
from bfabric_scripts.cli.api.read import cmd_api_read
from bfabric_scripts.cli.api.update import cmd_api_update

cmd_api = cyclopts.App(help="Commands for interacting with B-Fabric API directly.")
_ = cmd_api.command(cmd_api_create, name="create")
_ = cmd_api.command(cmd_api_delete, name="delete")
_ = cmd_api.command(cmd_api_read, name="read")
_ = cmd_api.command(cmd_api_update, name="update")
