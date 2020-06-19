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
        B = bfabric.Bfabric()

        logging.info("Running functional test on bfabricPy")

        msg = "This test case requires user 'pfeeder'."
        self.assertEqual(B.bflogin, 'pfeeder', msg)

        msg = "This test case requires a bfabric test system!"
        self.assertIn("bfabric-test", B.webbase, msg)
        # TODO
        # create input resource


        # 0. THIS IS ALL DONE PRIOR TO THE APPLICATION LAUNCH USING WEB BROWSER
        logging.info("Creating new executable")
        try:
            executable = B.save_object("executable", obj={"name": "exec_func_test", "context": "APPLICATION", "program": "/usr/bin/wc"})
            executableid = int(executable[0]._id)
        except:
            logging.error('Error while creating executable')

        logging.info("executableid = {}".format(executableid))
        msg = "executableid should be a positig integer."
        self.assertTrue(executableid > 0, msg)


        # The wrappercreatorid and submitterid is set while creating the application as required by B-Fabric, however this setting is not 
        # used in this functional test: BfabricWrapperCreator and BfabricSubmitter are calling directily below 
        logging.info("Creating new application")
        try:
            application =  B.save_object("application", obj={"name": "appl_func_test", 'type': 'Analysis', 'technologyid': 2, 'description': "Application functional test", 'executableid': executableid, "wrappercreatorid": 8, "submitterid": 5, 'storageid': 1, 'outputfileformat': 'txt'})
            applicationid = int(application[0]._id)
        except:
            logging.error('Error while creating application')

        logging.info("applicationid = {}".format(applicationid))
        msg = "applicationid should be a positig integer."
        self.assertTrue(applicationid > 0, msg)


        # 1. THIS CODE SNIPPET IS TRIGGERED BY THE BFABRIC SYSTEM AFTER THE USER RUN THE APPLICATION 
        logging.info("Creating new workunit")
        try:
            workunit = B.save_object("workunit",
                obj={"name": "unit test", "status": "pending", 'containerid': 3061, 'applicationid': applicationid, 'inputdatasetid': 32428})
            workunitid = int(workunit[0]._id)
        except:
            logging.error('Error while creating workunit')

        logging.info("workunit = {}".format(workunitid))
        msg = "workunitid should be a positig integer."
        self.assertTrue(workunitid > 0, msg)

        logging.info("Creating new externaljob")
        try:
            externaljob = B.save_object("externaljob", obj={'workunitid': workunitid, 'action': 'pending', 'executableid': executableid})
            externaljobid = int(externaljob[0]._id)
        except:
            logging.error("Error while creating externaljob")

        logging.info("externaljob = {}".format(externaljobid))
        msg = "extrernaljobid should be a positig integer."
        self.assertTrue(externaljobid > 0)

        logging.info("Running write_yaml from WrapperCreator")
        ## this information is contained in the application definition
        try:
            W = bfabric.BfabricWrapperCreator(externaljobid=externaljobid)
            W.write_yaml()
        except:
            logging.error("Error while running WrapperCreator")
            #logging.info('Removing executableid {}'.format(executableid))
            #res = B.delete_object('executable', executableid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)
            #logging.info('Removing applicationid {}'.format(applicationid))
            #res = B.delete_object('application', applicationid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)
            #logging.info('Removing workunit {}'.format(workunitid))
            #res = B.delete_object('workunit', workunitid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)

        logging.info("Running submitter_yaml from Submitter")
        S = bfabric.BfabricSubmitter(externaljobid=externaljobid)
        ## this information is contained in the application definition
        try:
            S.submitter_yaml()
        except:
            logging.error("Error while running Submitter")



        # 2.
        ###### 

        # TODO(cp): lets have a simple word count on the dataset or input resources for demonstration
        # HERE ALL THE MAGIC IS PROCESSED 


        # 2.1. stage input data
        # 2.2. run the job 
        # 2.3. stage the output data to the storage defined in the application (YAML file contains already that information)

        ######


        # 3. THIS LINE IST CALLED WHEN THE APPLICATION IS DONE
        ## TODO(cp): ask Can or Marco if this is correct
        logging.info("Updating externaljob status to Done")
        try:
            res = B.save_object('externaljob', {'id': externaljobid, 'status':'done'})
            print(res[0])
            self.assertEqual(res[0].status, 'done', 'functional application test failed.')
        except:
            logging.error("Error while setting status to done")
            #logging.info('Removing executableid {}'.format(executableid))
            #res = B.delete_object('executable', executableid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)
            #logging.info('Removing applicationid {}'.formatapplicationid))
            #res = B.delete_object('application', applicationid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)
            #logging.info('Removing workunit {}'.format(workunitid))
            #res = B.delete_object('workunit', workunitid)
            #print(res[0])
            #self.assertIn("removed successfully", res[0].deletionreport)



        # Cleanup for the python test whatever is possible can be removed
        # externaljobid, workunitid, ...
        res = B.delete_object('executable', executableid)
        print(res[0])
        self.assertIn("removed successfully", res[0].deletionreport)

        res = B.delete_object('application', applicationid)
        print(res[0])
        self.assertIn("removed successfully", res[0].deletionreport)

        res = B.delete_object('workunit', workunitid)
        print(res[0])
        self.assertIn("removed successfully", res[0].deletionreport)

        res = B.delete_object('externaljob', externaljobid)
        print(res[0])
        msg = "should fail"
        self.assertNotIn("removed successfully", res[0].deletionreport)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(BfabricFunctionalTestCase('test_wrappercreator_submitter'))

    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite )

