
"""

B-Fabric Appliaction Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

Copyright (C) 2014, 2015, 2016, 2017, 2018, 2019, 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Authors:
    Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$Id: setup.py 2997M 2017-08-21 13:04:42Z (local) $
$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/setup.py $
$Date: 2017-08-21 15:04:42 +0200 (Mon, 21 Aug 2017) $
$Revision: 2627 $

"""

from setuptools import setup
import bfabric

setup(name = 'bfabric',
      version = bfabric.__version__,
      description="""
B-Fabric Appliaction Interface using WSDL. The code contains classes for wrapper_creator and submitter.
""",
      url='git@github.com:cpanse/bfabricPy.git ',
      author='Christian Panse',
      author_email='cp@fgcz.ethz.ch',
      license='GPLv3 / apache 2.0',
      packages=['bfabric'],
      python_requires=">=3.6",
      install_requires=[
        'Flask>=1.0.3',
        'PyYAML>=3.11',
        'suds-py3==1.3.1',
        'slugify'
        ],
      scripts=[
        'bfabric/scripts/bfabric_delete.py',
        'bfabric/scripts/bfabric_read.py',
        'bfabric/scripts/bfabric_flask.py',
        'bfabric/scripts/bfabric_save_resource.py'
        #'bfabric/scripts/bfabric_list_executables.py',
        #'bfabric/scripts/bfabric_list_proteomics_projects.py',
        #'bfabric/scripts/bfabric_upload_wrapper_creator_executable.py',
        #'bfabric/scripts/bfabric_upload_submitter_executable.py',
        #'bfabric/scripts/bfabric_upload_resource.py',
        #'bfabric/scripts/bfabric_create_bfabricrc.py',
        #'bfabric/scripts/bfabric_save_importresource.py',
        ##'bfabric/scripts/bfabric_save_importresource_mascot.py',
        #'bfabric/scripts/bfabric_save_fasta.py',
        #'bfabric/scripts/bfabric_setExternalJobStatus_done.py',
        #'bfabric/scripts/bfabric_setResourceStatus_available.py',
        #'bfabric/scripts/bfabric_setWorkunitStatus_available.py',
        #'bfabric/scripts/bfabric_wrapper_creator_yaml.py',
        #'bfabric/scripts/bfabric_submitter_yaml.py',
        #'bfabric/scripts/bfabric_save_importresource_sample.py'
        #'bfabric/scripts/bfabric_feeder_resource_autoQC'
        #'bfabric/scripts/fgcz_maxquant_wrapper.py'
        ],
      zip_safe=True)
