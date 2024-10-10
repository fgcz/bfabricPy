from __future__ import annotations

import cyclopts

from bfabric.experimental.app_interface.cli.app import app_app
from bfabric.experimental.app_interface.cli.chunk import app_chunk
from bfabric.experimental.app_interface.cli.inputs import app_inputs
from bfabric.experimental.app_interface.cli.outputs import app_outputs
from bfabric.experimental.app_interface.cli.validate import app_validate

app = cyclopts.App(help="Provides an entrypoint to app execution.\n\nFunctionality/API under active development!")
app.command(app_inputs)
app.command(app_outputs)
app.command(app_app)
app.command(app_chunk)
app.command(app_validate)

if __name__ == "__main__":
    app()
