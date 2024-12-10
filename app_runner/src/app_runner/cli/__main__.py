from __future__ import annotations

import importlib.metadata

import cyclopts

from app_runner.cli.app import app_app
from app_runner.cli.chunk import app_chunk
from app_runner.cli.inputs import app_inputs
from app_runner.cli.outputs import app_outputs
from app_runner.cli.validate import app_validate

package_version = importlib.metadata.version("app_runner")

app = cyclopts.App(
    help="Provides an entrypoint to app execution.\n\nFunctionality/API under active development!",
    version=package_version,
)
app.command(app_inputs)
app.command(app_outputs)
app.command(app_app)
app.command(app_chunk)
app.command(app_validate)

if __name__ == "__main__":
    app()
