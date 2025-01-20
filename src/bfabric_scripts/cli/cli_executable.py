import cyclopts

from bfabric_scripts.cli.executable.inspect import inspect_executable
from bfabric_scripts.cli.executable.upload import upload_executable

app = cyclopts.App()
app.command(inspect_executable, name="inspect")
app.command(upload_executable, name="upload")
