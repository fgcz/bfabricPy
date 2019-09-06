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
    def __init__(self, *args, **kwargs):
        super(BfabricTestCase, self).__init__(*args, **kwargs)

        self.bfapp = bfabric.Bfabric(verbose=False)
        self.workunits = []
        self.resources = []
        self.samples = []

    def workunit_save(self):
        queue = range(1, 4)
        for j in queue:
            res = self.bfapp.save_object(endpoint='workunit', obj={'name': "unit test - #{}.".format(j),
                                                                   'containerid': bfabric.project,
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940',
                                                                   'applicationid': bfabric.application
                                                                   })
            for i in res:
                try:
                    self.workunits.append(i._id)
                    self.resource_save(os.path.abspath(__file__), i._id)
                except:
                    raise
        self.assertEqual(len(queue), len(self.workunits))


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

        for i in res:
            try:
                self.resources.append(i._id)
            except:
                raise


    def workunit_read(self):
        res = [self.bfapp.read_object(endpoint='workunit', obj={'id': x}) for x in self.workunits]
        res = [x for x in res if x[0].description == '68b329da9893e34099c7d8ad5cb9c940']
        self.assertEqual(len(res), len(self.workunits))

    def resource_delete(self):
        print (self.resources)
        res = [self.bfapp.delete_object(endpoint='resource', id=x)[0] for x in self.resources]
        res = [x for x in res if "removed successfully." in x.deletionreport]
        self.assertEqual(len(res), len(self.resources))

    def workunit_delete(self):
        res = [self.bfapp.delete_object(endpoint='workunit', id=x)[0] for x in self.workunits]
        res = [x for x in res if "removed successfully." in x.deletionreport]
        self.assertEqual(len(res), len(self.workunits))

    def test_executable(self, filename=os.path.abspath(__file__)):
        with open(filename, 'r') as f:
            executable = f.read()

        attr = { 'name': 'unit test', 
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

        res0 = self.bfapp.save_object('executable', attr)
        res1 = self.bfapp.read_object('executable', obj={'id': res0[0]._id})

        self.assertEqual(18, len(res1[0]))

    def sample_save(self):
        print("SAVE SAMPLE")
        #sample_type = 'Biological Sample - Proteomics'
        sample_type = 'Proteomics'
        species = "n/a"
        for name in [1, 2, 3]:
            res = self.bfapp.save_object(endpoint='sample',
                obj={'name': "unit test - #{}; {}".format(name, sample_type),
                    'containerid': 3000,
                    'type' : sample_type,
                    'species' : species,
                    'samplingdate' : "2017-10-12",
                    'groupingvar' : "A",
                    'description': '68b329da9893e34099c7d8ad5cb9c940'
                    })

            #print(res[0]._id)
            print("=== BEGIN DEBUG")
            for i in res:
                print (i)
                self.samples.append(res[0]._id)
            print("=== END DEBUG")

    def sample_delete(self):
        print (self.samples)
        res = [self.bfapp.delete_object(endpoint='sample', id=x)[0] for x in self.samples]
        res = [x for x in res if "removed successfully." in x.deletionreport]


    def test_sample(self):
        # self.sample_save()
        #self.sample_delete()
        pass

    def test_workunit(self):
        self.workunit_save()
        self.workunit_read()
        #self.resource_delete()
        self.workunit_delete()

if __name__ == '__main__':
    unittest.main()

