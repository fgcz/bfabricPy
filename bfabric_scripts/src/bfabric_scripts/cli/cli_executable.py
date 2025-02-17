import cyclopts

from bfabric_scripts.cli.executable.show import cmd_executable_show
from bfabric_scripts.cli.executable.upload import cmd_executable_upload

cmd_executable = cyclopts.App(help="Read and write executable entities in B-Fabric.")
cmd_executable.command(cmd_executable_show, name="show")
cmd_executable.command(cmd_executable_upload, name="upload")
