import cyclopts

from bfabric_scripts.cli.executable.show import cmd_executable_show
from bfabric_scripts.cli.executable.upload import cmd_executable_upload

app = cyclopts.App()
app.command(cmd_executable_show, name="show")
app.command(cmd_executable_upload, name="upload")
