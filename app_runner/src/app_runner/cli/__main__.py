from __future__ import annotations

import cyclopts

from app_runner.cli.app import app_app
from app_runner.cli.chunk import app_chunk
from app_runner.cli.inputs import app_inputs
from app_runner.cli.outputs import app_outputs
from app_runner.cli.validate import app_validate

app = cyclopts.App(help="Provides an entrypoint to app execution.\n\nFunctionality/API under active development!")
app.command(app_inputs)
app.command(app_outputs)
app.command(app_app)
app.command(app_chunk)
app.command(app_validate)

if __name__ == "__main__":
    app()
