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
import datetime

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

        self.bfapp = bfabric.Bfabric(verbose=False)

        for e in ['executable', 'sample', 'application', 'workunit', 'resource']:
            self.endpoint[e] = []

    def resource_save(self, filename, workunitid):
        with open(filename, 'r') as f:
            content = f.read()

        try:
            resource_base64 = base64.b64encode(content.encode())
        except:
            raise ("error: could not encode content")

        res = self.bfapp.save_object('resource',
            {'base64': resource_base64,
            'name': os.path.basename(filename),
            'description': content,
            'workunitid': workunitid})

        self.endpoint['resource'].append(res[0])


    def delete_endpoint_entries(self, endpoint=None):
        res = [ self.bfapp.delete_object(endpoint=endpoint, id=x._id)[0] for x in self.endpoint[endpoint] ]
        print(json.dumps(res, cls=bfabricEncoder, indent=2))
        res = [x for x in res if "removed successfully." in x.deletionreport]
        self.assertEqual(len(res), len(self.endpoint[endpoint]))

    def _01_executable_save(self, filename=os.path.abspath(__file__)):
        with open(filename, 'r') as f:
            executable = f.read()

        query = { 'name': 'unit test',
                  'context': 'APPLICATION',
                  'parameter': {'modifiable': 'true',
                                'description': 'will be ignored.',
                                'key': 'argument1',
                                'label': 'argument1',
                                'required': 'true',
                                'type':'string',
                                'value': 'PRX@fgcz-r-028'},
                  'description': 'python3 unit test executable.',
                  #'masterexecutableid': 11871,
                  'base64': base64.b64encode(executable.encode()) }

        res = self.bfapp.save_object('executable', query)[0]
        print (res)
        self.endpoint['executable'].append(res)

    def _02_sample_save(self):
        sample_type = 'Biological Sample - Proteomics'
        species = "n/a"
        for name in [1, 2, 3]:
            res = self.bfapp.save_object(endpoint='sample',
                obj={'name': "unit test - #{}; {} {}".format(name, sample_type, datetime.datetime.now()),
                    'containerid': 3000,
                    'type' : sample_type,
                    'species' : species,
                    'samplingdate' : "2017-10-12",
                    'groupingvar' : "A",
                    'description': '68b329da9893e34099c7d8ad5cb9c940'
                    })

            print(res[0])
            self.endpoint['sample'].append(res[0])


    def _03_application_save(self):
        query={'name': "unit test",
                    'description': '68b329da9893e34099c7d8ad5cb9c940',
                    'type': "Analysis",
                    'technologyid' : 2
                    }

        res = self.bfapp.save_object(endpoint='application', obj=query)
        print(json.dumps(res, cls=bfabricEncoder, indent=2))
        self.endpoint['application'].append(res[0])


    def _04_workunit_save(self):
        queue = range(1, 4)
        try:
            applicationid = self.endpoint['application'][0]._id
        except:
            applicationid = 61
        for j in queue:
            res = self.bfapp.save_object(endpoint='workunit', obj={'name': "unit test - #{}.".format(j),
                                                                   'containerid': bfabric.project,
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940',
                                                                   'applicationid': applicationid
                                                                   })
            self.endpoint['workunit'].append(res[0])
            print(json.dumps(self.endpoint['workunit'], cls=bfabricEncoder, indent=2))
            self.resource_save(os.path.abspath(__file__), res[0]._id)

        #self.assertEqual(len(queue), len(self.workunits))

        
    def _98_statistics(self):
        print("\nsummary:")
        for k, v in self.endpoint.items():
            try:
                res = [x._id for x in v]
                print ("{}\n\t{}".format(k,  [x._id for x in v]))
            except:
                pass

    def test_01(self):
        self._01_executable_save()
        self._02_sample_save()
        self._03_application_save()
        self._04_workunit_save()
        self._98_statistics()


        self.delete_endpoint_entries(endpoint='executable')
        self.delete_endpoint_entries(endpoint='sample')
        self.delete_endpoint_entries(endpoint='workunit')
        #self.delete_endpoint_entries(endpoint='application')


if __name__ == '__main__':
    unittest.main(verbosity=2)

