import importlib.metadata

__version__ = importlib.metadata.version("bfabric")

name = "bfabricPy"


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

from bfabric.bfabric_legacy import Bfabric
from bfabric.wrapper_creator.bfabric_wrapper_creator import BfabricWrapperCreator
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter
from bfabric.wrapper_creator.bfabric_feeder import BfabricFeeder
from bfabric.bfabric_config import BfabricConfig
