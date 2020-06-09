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
        # create application
        # create application executable
        # create input resource

        workunit = B.save_object("workunit",
            obj={"name": "unit test", "status": "pending", 'containerid': 3000, 'applicationid': 255})

        workunitid = int(workunit[0]._id)
        msg = "workunitid should be a positig integer."
        self.assertTrue(workunitid > 0, msg)

        externaljob = B.save_object("externaljob", obj={'workunitid': workunitid, 'action': 'pending'})
        externaljobid = int(externaljob[0]._id)
        msg = "extrernaljobid should be a positig integer."
        self.assertTrue(externaljobid > 0)

        W = bfabric.BfabricWrapperCreator(externaljobid=externaljobid)
        W.write_yaml()

        S = bfabric.BfabricSubmitter(externaljobid=externaljobid)
        S.submitter_yaml()



        res = B.save_object('externaljob', {'id': externaljobid, 'status':'done'})
        print(res[0])
        self.assertEqual(res[0].status, 'done', 'functional application test failed.')


        # Cleanup
        # externaljobid, workunitid, ...
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

