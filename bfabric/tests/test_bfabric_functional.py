#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
"""

import base64
import unittest
import bfabric
import os

class BfabricFunctionalTestCase(unittest.TestCase):


    externaljobid = 0

    def __init__(self, *args, **kwargs):
        super(BfabricFunctionalTestCase, self).__init__(*args, **kwargs)


    def test_wrappercreator_submitter(self):
        B = bfabric.Bfabric()


        msg = "This test case requires user 'pfeeder'."
        self.assertEqual(B.bflogin, 'pfeeder', msg)

        msg = "This test case requires a bfabric test system!"
        self.assertIn("bfabric-test", B.webbase, msg)
        # TODO
        # create input resource


        # 0. THIS IS ALL DONE PRIOR TO THE APPLICATION LAUNCH USING WEB BROWSER
        executable = B.save_object("executable", obj={"name": "exec_func_test", "context": "APPLICATION"})

        executableid = int(executable[0]._id)
        msg = "executableid should be a positig integer."
        self.assertTrue(executableid > 0, msg)

        application = B.save_object("application", obj={"name": "appl_func_test", 'type': 'Analysis', 'technologyid': 2, 'description': "Application functional test", 'executableid': executableid})
        # just a template
        #  B.save_object("application", obj={"name": "appl_func_test", 'type': 'Analysis', 'technologyid': 2, 'description': "Application functional test", 'executableid': 20714, "wrappercreatorid":8, "submitterid":5 , 'storageid': 1})
        ## a=  B.save_object("application", obj={"name": "appl_func_test", 'type': 'Analysis', 'technologyid': 2, 'description': "Application functional test", 'executableid': 20714, "wrappercreatorid":8, "submitterid":5 , 'storageid': 1, 'id': 299})

        applicationid = int(application[0]._id)
        msg = "applicationid should be a positig integer."
        self.assertTrue(applicationid > 0, msg)


        # 1. THIS CODE SNIPPET IS TRIGGERED BY THE BFABRIC SYSTEM AFTER THE USER RUN THE APPLICATION 
        workunit = B.save_object("workunit",
            obj={"name": "unit test", "status": "pending", 'containerid': 3061, 'applicationid': applicationid, 'inputdatasetid': 32428})

        workunitid = int(workunit[0]._id)
        msg = "workunitid should be a positig integer."
        self.assertTrue(workunitid > 0, msg)

        externaljob = B.save_object("externaljob", obj={'workunitid': workunitid, 'action': 'pending'})
        externaljobid = int(externaljob[0]._id)
        msg = "extrernaljobid should be a positig integer."
        self.assertTrue(externaljobid > 0)

        W = bfabric.BfabricWrapperCreator(externaljobid=externaljobid)
        ## this information is contained in the application definition
        W.write_yaml()

        S = bfabric.BfabricSubmitter(externaljobid=externaljobid)
        ## this information is contained in the application definition
        S.submitter_yaml()



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
        res = B.save_object('externaljob', {'id': externaljobid, 'status':'done'})
        print(res[0])
        self.assertEqual(res[0].status, 'done', 'functional application test failed.')


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

