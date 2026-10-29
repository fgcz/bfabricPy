import importlib.metadata
import warnings

from bfabric.bfabric import Bfabric
from bfabric.config.base_url import BaseUrl
from bfabric.config.bfabric_auth import BfabricAuth
from bfabric.config.bfabric_client_config import BfabricAPIEngineType, BfabricClientConfig

# polars only warns about missing CPU features and then dies with SIGILL; raise its install hint instead
warnings.filterwarnings("error", message="Missing required CPU features", category=RuntimeWarning)

__all__ = [
    "BaseUrl",
    "Bfabric",
    "BfabricAPIEngineType",
    "BfabricAuth",
    "BfabricClientConfig",
]

__version__ = importlib.metadata.version("bfabric")
