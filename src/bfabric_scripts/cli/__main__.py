import cyclopts
from bfabric_scripts.cli.cli_read import app as _app_read


app = cyclopts.App()
app.command(_app_read, name="read")

if __name__ == "__main__":
    app()
