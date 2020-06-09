#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
"""

import base64
import unittest
import bfabric
import os

class BfabricTestCase(unittest.TestCase):


    externaljobid = 0

    def __init__(self, *args, **kwargs):
        super(BfabricTestCase, self).__init__(*args, **kwargs)


    def test_wrappercreator_submitter(self):
        B = bfabric.Bfabric()


        # TODO
        # create application
        # create application executable
        # create input resource

        workunit = B.save_object("workunit",
            obj={"name": "unit test", "status": "pending", 'containerid': 3000, 'applicationid': 255})

        workunitid = int(workunit[0]._id)
        self.assertTrue(workunitid > 0)

        externaljob = B.save_object("externaljob", obj={'workunitid': workunitid, 'action': 'pending'})
        externaljobid = int(externaljob[0]._id)
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
        # self.assertIn("removed successfully", res[0].deletionreport)


if __name__ == '__main__':
    unittest.main(verbosity=2)

