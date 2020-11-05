#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
"""

import base64
import unittest
import bfabric
import os
import sys
import logging
import time


logging.basicConfig(filename="test_functional.log",
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

class BfabricFunctionalTestCase(unittest.TestCase):


    externaljobid = 0

    def __init__(self, *args, **kwargs):
        super(BfabricFunctionalTestCase, self).__init__(*args, **kwargs)


    def test_wrappercreator_submitter(self):
        logging.info("XXX start functional testing")
        B = bfabric.Bfabric()

        logging.info("Running functional test on bfabricPy")

        msg = "This test case requires user 'pfeeder'."
        self.assertEqual(B.bflogin, 'pfeeder', msg)

        msg = "This test case requires a bfabric test system!"
        self.assertIn("bfabric-test", B.webbase, msg)
        # TODO
        # create input resource


        # 0. THIS IS ALL DONE PRIOR TO THE APPLICATION LAUNCH
        # 0.1
        logging.info("Creating a new executable for the test application")
        executable = B.save_object("executable", obj={"name": "exec_func_test", "context": "APPLICATION", "program": "/usr/bin/wc"})
        try:
            if executable[0].errorreport:
                logging.error("Error while creating the executable")
                logging.info('Errorreport present: {}'.format(executable[0].errorreport))
                raise
        except:
            logging.info('Executable successfully created')
        try:
            executableid = int(executable[0]._id)
            logging.info("executableid = {}".format(executableid))
        except:
            logging.error('Error while getting the executable id')

        msg = "executableid should be a positig integer."
        self.assertTrue(executableid > 0, msg)

        # 0.2
        logging.info("Creating a new test application, mimicking the user application")
        # In order to create the application, wrappercreatorid and submitterid must be provided.
        # Note that: in this specific case the wrappercreatorid is a placeholder, and it will be replaced by a test executable later in this functional test.
        # The executable for submitterid=10 has been created in the test system running the following script:
        # ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py gridengine --name "Dummy - yaml / Grid Engine executable" --description "Dummy submitter for the bfabric functional test using Grid Engine."
        # Note that the executable bfabric_executable_submitter_functionalTest.py only prints "Dummy submitter executable defined for the bfabricPy functional test".
        application =  B.save_object("application", obj={"name": "appl_func_test", 'type': 'Analysis', 'technologyid': 2, 'description': "Application functional test", 'executableid': executableid, "wrappercreatorid": 8, "submitterid": 10, 'storageid': 1, 'outputfileformat': 'txt'})
        try: 
            if application[0].errorreport:
                logging.error("Error while creating the application")
                logging.info('Errorreport present: {}'.format(application[0].errorreport))
                raise
        except:
            logging.info('Application successfully created')
        try:
            applicationid = int(application[0]._id)
            logging.info("applicationid = {}".format(applicationid))
        except:
            logging.error('Error while getting the application id')
            raise

        msg = "applicationid should be a positig integer."
        self.assertTrue(applicationid > 0, msg)


        # 1. THIS CODE SNIPPET IS TRIGGERED BY THE BFABRIC SYSTEM AFTER THE USER RUN THE APPLICATION 
        # 1.1
        logging.info("Creating new workunit connecting the test application executable to the execution anvironment")
        workunit = B.save_object("workunit",
                obj={"name": "unit test run - bfabricPy",
                    "status": "PENDING", 'containerid': 3061,
                    'applicationid': applicationid,
                    'description': "https://github.com/fgcz/bfabricPy/blob/iss27/bfabric/tests/test_bfabric_functional.py",
                    'inputdatasetid': 32428})
        try:
            if workunit[0].errorreport:
                logging.error('Error while creating workunit')
                logging.info('Errorreport present: {}'.format(workunit[0].errorreport))
                raise
        except:
            logging.info('Workunit successfully created')
        try:
            workunitid = int(workunit[0]._id)
            logging.info("workunit = {}".format(workunitid))
        except:
            logging.error('Error while getting the workunit id')
            raise

        msg = "workunitid should be a positig integer."
        self.assertTrue(workunitid > 0, msg)

        # 2. B-FABRIC TRIGGERS THE WRAPPERCREATOR
        # 2.1
        logging.info("Creating new externaljob for the WrapperCreator executable")
        # Here a precomputed test executable is replacing the wrappercreatorid in the application definition
        wrapper_creator_executableid = 16374
        externaljob_wc = B.save_object("externaljob", obj={'workunitid': workunitid, 'action': 'CREATE', 'executableid':  wrapper_creator_executableid})
        try:
            if externaljob_wc[0].errorreport:
                logging.error('Error while creating externaljob_wc')
                logging.info('Errorreport present: {}'.format(externaljob_wc[0].errorreport))
                raise
        except:
            logging.info('Externaljob_wc successfully created')
        try:
            externaljobid_wc = int(externaljob_wc[0]._id)
            logging.info("externaljob = {}".format(externaljobid_wc))
        except:
            logging.error("Error while getting externaljob_wc id")
            raise

        msg = "extrernaljobid should be a positig integer."
        self.assertTrue(externaljobid_wc > 0)

        # 2.2
        logging.info("Executing the WrapperCreator executable: function write_yaml from BfabricWrapperCreator")
        # The following steps will be executed by the write_yaml:
        # - Creates a workunit executable (yaml_workunit_executable), and registers it in B-Fabric
        # - Creates an externaljob (yaml_workunit_externaljob) for the workunit executable
        # - Inherits all parameters of the application executable
        # - Composes configuration structure in Yaml format
        # - If the WrapperCreator executable is successful, it sets the status of its external job (externaljob_wc) to done,
        #   which triggers B-Fabric to create an external job for the submitter executable and to trigger it

        ## this information is contained in the application definition
        try:
            W = bfabric.BfabricWrapperCreator(externaljobid=externaljobid_wc)
            W.write_yaml()
            # TODO(cp): write getter of execuableid
        except:
            logging.error("Error while running WrapperCreator")

        logging.info("Checking if wrapper creator's externaljob with id={} was set to 'done'".format(externaljobid_wc))
        try:
            res = B.read_object('externaljob', {'id': externaljobid_wc, 'status':'DONE'})
            self.assertEqual(res[0].status, 'done', 'set externaljob id={} of wrapper creator failed.'.format(externaljobid_wc))
        except:
            logging.error("Error while setting wrapper creator's externaljob status to done")

        # 2.3
        logging.info("Fetching the id of the yaml_workunit_externaljob in order to set it as DONE at the end of this functional test")
        try:
            # The method W.get_externaljobid_yaml_workunit() returns the external job with Action=WORKUNIT
            externaljobid_yaml_workunit = W.get_externaljobid_yaml_workunit()
            logging.info("Externaljobid with action WORKUNIT is {}".format(externaljobid_yaml_workunit))
        except:
            logging.error("Error while fetching the id of the yaml_workunit externaljob")

        # 3. B-FABRIC TRIGGERS THE SUBMITTER
        # 3.1
        logging.info("Fetching the submitter's externaljob automatically triggered by B-Fabric")
        try:
            externaljobid_submitter = B.read_object('externaljob', {'cliententityid': workunitid, "action": "SUBMIT", 'cliententityclass': 'Workunit'})[0]._id
            logging.info("externaljobid for submitter is {}.".format(externaljobid_submitter))
        except:
            logging.error("Error while fetching the id of the submitter's externaljob")

        # 3.2
        logging.info("Executing the Submitter executable: function submitter_yaml from BfabricSubmitter")
        # Submitter executable is supposed to download all workunit executables and submit them.
        # When finished successfully, the status of its external job is set to done, else to failed.
        S = bfabric.BfabricSubmitter(externaljobid=externaljobid_submitter)
        ## this information is contained in the application definition
        try:
            S.submitter_yaml()
        except:
            logging.error("Error while running Submitter")
            raise

        logging.info("Checking if submitter's externaljob with id={} was set to 'done'".format(externaljobid_submitter))
        try:
            res = B.read_object('externaljob', {'id': externaljobid_submitter, 'status': 'DONE'})
            self.assertEqual(res[0].status, 'done', 'submitter externaljob with id={} failed.'.format(externaljobid_submitter))
        except:
            logging.error("Error while setting submitter externaljob status to DONE")
            raise

        # 4. SETTING YAML_WORKUNIT_EXTERNALJOB TO DONE
        logging.info("Setting the yaml_workunit_externaljob created by the WrapperCreator to 'done'")
        try:
            res = B.save_object(endpoint='externaljob', obj={'id': externaljobid_yaml_workunit, 'status': 'done'})
            logging.info("Checking if WORKUNIT's externaljob with id={} was set to 'done'".format(externaljobid_yaml_workunit))
            res = B.read_object('externaljob', {'id': externaljobid_yaml_workunit, 'status':'DONE'})
            self.assertEqual(res[0].status, 'done', 'yaml_workunit_externaljob with id={} failed.'.format(externaljobid_yaml_workunit))
        except:
            logging.error("Error while setting yaml_workunit externaljob status to done")

        # 5.
        # Let's have a simple word count on the dataset or input resources for demonstration
        # 5.1. stage input data
        # 5.2. run the job
        # 5.3. stage the output data to the storage defined in the application (YAML file contains already that information)

        logging.info("Start processing job.")
        for i in S.get_job_script():
            logging.info("processing file '{}' ...".format(i))
            time.sleep(1)
        logging.info("end processing job.")


        logging.info("Deleting superfluous resources of test run workunit.")
        res = B.read_object('workunit', {'id',  workunit[0]._id})[0]
        for i in res.resource:
            resdel = B.delete_object('resource', i._id)
            self.assertIn("removed successfully", resdel[0].deletionreport)
            logging.info("deleted resource id={}.".format(i._id))

        logging.info("adding this logfile as resource to workuinit id={}.".format(workunit[0]._id))
        res = B.upload_file("test_functional.log", workunit[0]._id)
        self.assertTrue(res[0]._id > 0, msg)

        ######

        # 6. THIS LINE IS CALLED WHEN THE APPLICATION IS DONE
        ## TODO(cp): ask Can or Marco if this is correct


        logging.info("Cleanup for the python test: whatever is possible to be removed")
        res = B.delete_object('executable', executableid)
        self.assertNotIn("removed successfully", res[0].deletionreport)

        res = B.delete_object('application', applicationid)
        self.assertNotIn("removed successfully", res[0].deletionreport)

        res = B.save_object('workunit', {'id': workunitid, 'status': 'available'})

        res = B.delete_object('externaljob', externaljobid_submitter)
        msg = "should fail"
        self.assertNotIn("removed successfully", res[0].deletionreport)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(BfabricFunctionalTestCase('test_wrappercreator_submitter'))

    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite )

