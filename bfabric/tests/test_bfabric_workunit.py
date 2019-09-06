#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <cp@fgcz.ethz.ch>
"""

import unittest
import bfabric


class BfabricTestCase(unittest.TestCase):
    workunits = []
    samples = []

    bfapp = bfabric.Bfabric(verbose=False)

    def workunit_save(self):
        print("WORKUNIT SAVE")
        for j in range(1,10):
            res = self.bfapp.save_object(endpoint='workunit', obj={'name': "unit test - #{}.".format(j),
                                                                   'containerid': 3000,
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940',
                                                                   'applicationid': 217
                                                                   })

            for i in res:
                try:
                    print(i._id)
                    print(i)
                    self.workunits.append(i._id)
                    print("YEAH")
                except:
                    pass
            
        #print(self.workunits)


    def workunit_read(self):
        print("WORKUNIT READ")
        print (self.workunits)
        res = [self.bfapp.read_object(endpoint='workunit', obj={'id': x}) for x in self.workunits]
        res = [x for x in res if x[0].description == '68b329da9893e34099c7d8ad5cb9c940']
        self.assertEqual(len(res), len(self.workunits))

    def workunit_delete(self):
        print("WORKUNIT DELETE")
        res = [self.bfapp.delete_object(endpoint='workunit', id=x)[0] for x in self.workunits]
        res = [x for x in res if "removed successfully." in x.deletionreport]
        print(res)
        self.assertEqual(len(res), len(self.workunits))

    def test_workunit(self):
        self.workunit_save()
        self.workunit_read()
        self.workunit_delete()

if __name__ == '__main__':
    unittest.main()
