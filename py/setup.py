from setuptools import setup

"""

B-Fabric Appliaction Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

Copyright (C) 2014, 2015, 2016, 2017 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Authors:
    Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$Id: setup.py 2641 2017-02-24 13:46:11Z cpanse $
$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/setup.py $
$Date: 2017-02-24 14:46:11 +0100 (Fri, 24 Feb 2017) $
$Revision: 2627 $

"""




setup(name='bfabric',
      version='0.4.4',
      description="""
B-Fabric Appliaction Interface using WSDL. The code contains classes for wrapper_creator and submitter.
""",
      url='http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python',
      author='Christian Panse',
      author_email='cp@fgcz.ethz.ch',
      license='GPLv3 / apache 2.0',
      packages=['bfabric'],
      install_requires=[
        'Flask>=0.11.1',
        'PyYAML>=3.11',
        'suds==0.4'
        ],
      scripts=[
        'bfabric/scripts/fgcz_bfabric_setResourceStatus_available.py',
        'bfabric/scripts/fgcz_bfabric_setExternalJobStatus_done.py',
        'bfabric/scripts/bfabric_list_executables.py',
        'bfabric/scripts/bfabric_list_failed_workunits.py',
        'bfabric/scripts/bfabric_list_pending_workunits.py',
        'bfabric/scripts/bfabric_list_proteomics_projects.py',
        'bfabric/scripts/bfabric_list.py',
        'bfabric/scripts/bfabric_upload_wrapper_creator_executable.py',
        'bfabric/scripts/bfabric_upload_submitter_executable.py',
        'bfabric/scripts/bfabric_flask_wuid_resources.py',
        'bfabric/scripts/bfabric_flask_sample.py',
        'bfabric/scripts/bfabric_create_bfabricrc.py',
        'bfabric/scripts/bfabric_delete.py',
        'bfabric/scripts/bfabric_save_importresource.py',
        'bfabric/scripts/bfabric_setExternalJobStatus_done.py'
        ],
      zip_safe=True)
