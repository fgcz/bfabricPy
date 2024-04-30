import importlib.metadata

__version__ = importlib.metadata.version("bfabric")

name = "bfabricPy"
alias = "suds-py3"

msg = "\033[93m{} version {} (2023-11-03) -- \"{}\"\
    \nCopyright (C) 2014-2023 Functional Genomics Center Zurich\033[0m\n\n"\
    .format(name, __version__, alias)

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

from bfabric.bfabric import Bfabric
from bfabric.bfabric import BfabricWrapperCreator
from bfabric.bfabric import BfabricSubmitter
from bfabric.bfabric import BfabricFeeder
from bfabric.bfabric_config import BfabricConfig
