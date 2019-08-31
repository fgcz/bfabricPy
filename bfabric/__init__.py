name = "bfabricPy"
alias = "suds-py3"
version = "0.10.1"

msg = "\033[93m{} version {} (2019-08-31) -- \"{}\"\
    \nCopyright (C) 2019 Functional Genomics Center Zurich\033[0m\n\n"\
    .format(name, version, alias)

endpoints = ['access', 'annotation', 'application',
        'attachement', 'comment', 'dataset', 'executable',
        'externaljob', 'groupingvar', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'storage', 'user', 'workunit', 'order', 'instrument']


from bfabric.bfabric import Bfabric
# import bfabric.gridengine as gridengine
#from bfabric import BfabricFeeder
#from bfabric import BfabricExternalJob
#from bfabric import BfabricSubmitter
#from bfabric import BfabricWrapperCreator


