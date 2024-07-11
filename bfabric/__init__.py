import importlib.metadata
from bfabric.bfabric import Bfabric, BfabricAPIEngineType
from bfabric.config.bfabric_client_config import BfabricClientConfig
from bfabric.config import BfabricAuth

__all__ = [
    "Bfabric",
    "BfabricAPIEngineType",
    "BfabricAuth",
    "BfabricConfig",
]


__version__ = importlib.metadata.version("bfabric")


endpoints = sorted(
    [
        "annotation",
        "application",
        "attachement",
        "barcodes",
        "charge",
        "comment",
        "container",
        "dataset",
        "executable",
        "externaljob",
        "groupingvar",
        "importresource",
        "instrument",
        "instrumentevent",
        "mail",
        "order",
        "parameter",
        "plate",
        "project",
        "resource",
        "sample",
        "storage",
        "user",
        "workflow",
        "workflowstep",
        "workunit",
    ]
)

# for unit tests
project = 403
container = project
application = 217
