"""

B-Fabric Appliaction Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

Copyright (C) 2014-2024 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Authors:
    Christian Panse <cp@fgcz.ethz.ch>
    Maria d'Errico <maria.derrico@fgcz.ethz.ch>

Licensed under  GPL version 3

"""

from setuptools import setup, find_packages
import os

with open('requirements.txt') as f:
    INSTALL_REQUIRES = f.read().splitlines()
ver_file = os.path.join('bfabric', '_version.py')
with open(ver_file) as f:
    exec(f.read())

VERSION = __version__

setup(name = 'bfabric',
      version = VERSION,
      description = """
B-Fabric Appliaction Interface using WSDL. The code contains classes for wrapper_creator and submitter.
""",
      url = 'git@github.com:fgcz/bfabricPy.git ',
      author = 'Christian Panse',
      author_email = 'cp@fgcz.ethz.ch',
      license = 'GPLv3 / apache 2.0',
      packages = ['bfabric'],
      python_requires = ">=3.9",
      install_requires = INSTALL_REQUIRES,
      scripts = [
        'bfabric/scripts/bfabric_flask.py',
        'bfabric/scripts/bfabric_feeder_resource_autoQC.py',
        'bfabric/scripts/bfabric_list_not_existing_storage_directories.py',
        'bfabric/scripts/bfabric_list_not_available_proteomics_workunits.py',
        'bfabric/scripts/bfabric_upload_resource.py',
        'bfabric/scripts/bfabric_logthis.py',
        'bfabric/scripts/bfabric_setResourceStatus_available.py',
        'bfabric/scripts/bfabric_setExternalJobStatus_done.py',
        'bfabric/scripts/bfabric_setWorkunitStatus_available.py',
        'bfabric/scripts/bfabric_setWorkunitStatus_processing.py',
        'bfabric/scripts/bfabric_setWorkunitStatus_failed.py',
        'bfabric/scripts/bfabric_delete.py',
        'bfabric/scripts/bfabric_read.py',
        'bfabric/scripts/bfabric_read_samples_of_workunit.py',
        'bfabric/scripts/bfabric_read_samples_from_dataset.py',
        'bfabric/scripts/bfabric_save_csv2dataset.py',
        'bfabric/scripts/bfabric_save_dataset2csv.py',
        'bfabric/scripts/bfabric_save_fasta.py',
        'bfabric/scripts/bfabric_save_importresource_sample.py',
        'bfabric/scripts/bfabric_save_link_to_workunit.py',
        'bfabric/scripts/bfabric_save_resource.py',
        'bfabric/scripts/bfabric_save_workunit_attribute.py',
        'bfabric/scripts/bfabric_save_workflowstep.py'
        ],
      zip_safe=True)

