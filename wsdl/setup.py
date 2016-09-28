from setuptools import setup


setup(name='bfabric',
      version='0.3.7',
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
        'bfabric/scripts/bfabric_list_executables.py',
        'bfabric/scripts/bfabric_upload_wrapper_creator_executable.py',
        'bfabric/scripts/bfabric_upload_submitter_executable.py',
        'bfabric/scripts/bfabric_flax_wuid_resources.py',
        'bfabric/scripts/bfabric_list_failed_workunits.py',
        'bfabric/scripts/bfabric_create_bfabricrc.py',
        'bfabric/scripts/bfabric_list_pending_workunits.py'
        ],
      zip_safe=True)
