import cyclopts

from bfabric_scripts.cli.executable.inspect import inspect_executable

app = cyclopts.App()
app.command(inspect_executable, name="inspect")
