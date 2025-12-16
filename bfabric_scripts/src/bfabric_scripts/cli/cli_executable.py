import cyclopts

from bfabric_scripts.cli.executable.dump import cmd_executable_dump
from bfabric_scripts.cli.executable.show import cmd_executable_show
from bfabric_scripts.cli.executable.upload import cmd_executable_upload

cmd_executable = cyclopts.App(help="Read and write executable entities in B-Fabric.")
_ = cmd_executable.command(cmd_executable_show, name="show")
_ = cmd_executable.command(cmd_executable_upload, name="upload")
_ = cmd_executable.command(cmd_executable_dump, name="dump")
