#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
2019-09-11
"""

import base64
import unittest
import bfabric
import os

class BfabricTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BfabricTestCase, self).__init__(*args, **kwargs)
        self.bfapp = bfabric.Bfabric(verbose=False)

        self.groundtruth = {'user' : [({'id': 482}, {'login': 'cpanse', 'email':'cp@fgcz.ethz.ch'})],
            'project' : [({'id': 3000}, {'name': 'FGCZ Internal'})],
            'application' : [({'id': 224}, {'name': 'MaxQuant'})],
            'resource' : [({'filechecksum': '090a3f025d3ebbad75213e3d4886e17c'}, {'name': '20190903_07_autoQC4L.raw'}), 
                ({'workunitid': 200186}, {'name': '20190618_07_autoQC4L.raw'})],
            'sample' : [({'id': 190249}, {'name': 'autoQC4L'})]
            }


    def read(self, endpoint):
        for (query, groundtruth) in self.groundtruth[endpoint]:
            res = self.bfapp.read_object(endpoint=endpoint, obj=query)
            for gtattr, gtvalue in groundtruth.items():
                #print ("{}:{} = {} \t?\t{}".format(endpoint, gtattr, gtvalue, getattr(res[0], gtattr)))
                self.assertEqual(gtvalue, getattr(res[0], gtattr))

    def test_user(self):
        self.read('user')
    def test_project(self):
        self.read('project')
    def test_application(self):
        self.read('application')
    def test_sample(self):
        self.read('sample')
    def test_resource(self):
        self.read('resource')

if __name__ == '__main__':
    unittest.main()

