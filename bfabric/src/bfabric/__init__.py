import importlib.metadata

from loguru import logger

from bfabric.bfabric import Bfabric
from bfabric.config.bfabric_auth import BfabricAuth
from bfabric.config.bfabric_client_config import BfabricAPIEngineType, BfabricClientConfig

# bfabric follows loguru's convention for libraries: it emits no log records unless the
# application opts in with ``logger.enable("bfabric")``. The command-line entry points do this
# via ``bfabric.utils.cli_integration.setup_script_logging``. This keeps library, server, and test
# contexts quiet by default -- most visibly the version banner logged on every client construction.
logger.disable("bfabric")

__all__ = [
    "Bfabric",
    "BfabricAPIEngineType",
    "BfabricAuth",
    "BfabricClientConfig",
]

__version__ = importlib.metadata.version("bfabric")
