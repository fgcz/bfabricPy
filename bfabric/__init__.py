from ._version import __version__

name = "bfabricPy"
alias = "suds-py3"

msg = "\033[93m{} version {} (2019-10-16) -- \"{}\"\
    \nCopyright (C) 2019 Functional Genomics Center Zurich\033[0m\n\n"\
    .format(name, __version__, alias)

endpoints = sorted(['access', 'annotation', 'application',
        'attachement', 'comment', 'container', 'dataset', 'executable',
        'externaljob', 'groupingvar', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'workflow', 'workflowstep',
        'storage', 'user', 'workunit', 'charge', 'order', 'instrument'])

# for unit tests
project=403
container=project
application=217

from bfabric.bfabric import Bfabric
from bfabric.bfabric import BfabricWrapperCreator
from bfabric.bfabric import BfabricSubmitter

