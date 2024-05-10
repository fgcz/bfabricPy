import importlib.metadata

__version__ = importlib.metadata.version("bfabric")

from bfabric.bfabric import Bfabric, BfabricAPIEngineType
from bfabric.bfabric_config import BfabricAuth, BfabricConfig


endpoints = sorted([
        'annotation',
        'application',
        'attachement',
        'barcodes',
        'charge',
        'comment',
        'container',
        'dataset',
        'executable',
        'externaljob',
        'groupingvar',
        'importresource',
        'instrument',
        'instrumentevent',
        'mail',
        'order',
        'parameter',
        'plate',
        'project',
        'resource',
        'sample',
        'storage',
        'user',
        'workflow',
        'workflowstep',
        'workunit'
])

# for unit tests
project = 403
container = project
application = 217


from bfabric.bfabric_legacy import BfabricLegacy
from bfabric.wrapper_creator.bfabric_wrapper_creator import BfabricWrapperCreator
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter
from bfabric.wrapper_creator.bfabric_feeder import BfabricFeeder
