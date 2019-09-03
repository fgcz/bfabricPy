__version__ = "0.10.3"

name = "bfabricPy"
alias = "suds-py3"

msg = "\033[93m{} version {} (2019-09-03) -- \"{}\"\
    \nCopyright (C) 2019 Functional Genomics Center Zurich\033[0m\n\n"\
    .format(name, __version__, alias)

endpoints = ['access', 'annotation', 'application',
        'attachement', 'comment', 'container', 'dataset', 'executable',
        'externaljob', 'groupingvar', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'storage', 'user', 'workunit', 'order', 'instrument']

from bfabric.bfabric import Bfabric
