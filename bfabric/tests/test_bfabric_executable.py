#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
"""

import base64
import unittest
import bfabric
import os
import json

class bfabricEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return dict(o)
        except TypeError:
            pass
        else:
            return list(o)
        return JSONEncoder.default(self, o)

class BfabricTestCase(unittest.TestCase):

    endpoint = {}


    def __init__(self, *args, **kwargs):
        super(BfabricTestCase, self).__init__(*args, **kwargs)

        self.B = bfabric.Bfabric(verbose=False)

        for e in ['executable', 'sample', 'application', 'workunit', 'resource']:
            self.endpoint[e] = []

    def delete_endpoint_entries(self, endpoint=None):
        res = [self.B.delete_object(endpoint=endpoint, id=x._id)[0] for x in self.endpoint[endpoint]]
        # print(json.dumps(res, cls=bfabricEncoder, indent=2))
        res = [x for x in res if "removed successfully." in x.deletionreport]
        self.assertEqual(len(res), len(self.endpoint[endpoint]))


    def test_executable(self, filename=os.path.abspath(__file__)):
        wu_res = self.B.save_object(endpoint='workunit', obj={'name': f"unit test - #{1234}.",
                                                                   'containerid': 3000,
                                                                   'description': 'unit test',
                                                                   'applicationid': 61
                                                                   })
        self.endpoint['workunit'].append(wu_res[0])
        # print(json.dumps(wu_res, cls=bfabricEncoder, indent=2))
        # save
        with open(filename, 'r') as f:
            executable = f.read()


        #executable = "echo 'hello, world!'"
        input_executable = executable

        input_b64_executable =  base64.b64encode(input_executable.encode()).decode()

        query = { 'name': 'unit test',
                  'context': 'WORKUNIT',
                  'parameter': {'modifiable': 'true',
                                'description': 'will be ignored.',
                                'key': 'argument1',
                                'label': 'argument1',
                                'required': 'true',
                                'type':'string',
                                'value': 'PRX@fgcz-r-028'},
                                'workunitid': wu_res[0]._id,
                  'description': 'python3 unit test executable.',
                  #'masterexecutableid': 11871,
                  'base64': input_b64_executable }

        self.endpoint['executable'].append(self.B.save_object('executable', query)[0])

        # read
        for e in self.endpoint['executable']:
            res = self.B.read_object('executable', obj={'id': e._id})
            output_b64_executable = res[0].base64

            output_executable = base64.b64decode(output_b64_executable.encode()).decode()


            self.assertEqual(input_b64_executable, output_b64_executable)
            self.assertEqual(input_executable, output_executable)

        # delete
        self.delete_endpoint_entries(endpoint='executable')
        self.delete_endpoint_entries(endpoint='workunit')


if __name__ == '__main__':
    unittest.main(verbosity=2)

