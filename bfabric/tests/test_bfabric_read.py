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
import json

class BfabricTestCase(unittest.TestCase):

    with open('groundtruth.json') as json_file:
        groundtruth = json.load(json_file)

    bfapp = bfabric.Bfabric(verbose=False)

    def __init__(self, *args, **kwargs):
        super(BfabricTestCase, self).__init__(*args, **kwargs)

    def read(self, endpoint):
        for (query, groundtruth) in self.groundtruth[endpoint]:
            res = self.bfapp.read_object(endpoint=endpoint, obj=query)
            for gtattr, gtvalue in groundtruth.items():
                if False:
                    print ("{}:{} = {} \t?\t{}".format(endpoint, gtattr, gtvalue, getattr(res[0], gtattr)))

                # to make it deterministic!
                try:
                    res = sorted(res, key = lambda x: x.id)
                except:
                    res = sorted(res, key = lambda x: x._id)

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

