#!/usr/bin/python 

"""
unittest by <cp@fgcz.ethz.ch>
"""

import unittest
from bfabric import Bfabric

"""
ssh localhost "cat > /tmp/bb.py && /usr/bin/python /tmp/bb.py" < PycharmProjects/untitled/bfabric_wsdl.py 
"""
class BfabricTestCase(unittest.TestCase):
    bfapp = Bfabric()

    workunits = []
    samples = []


    def workunit_save(self):
        print "WORKUNIT SAVE"
        for name in ['test1', 'test2', 'test3']:
            res = self.bfapp.save_object(endpoint='workunit', obj={'name': "unit test - {}".format(name),
                                                                   'projectid': 1000,
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940',
                                                                   'applicationid': 217
                                                                   })

            self.workunits.append(res[0]._id)
        print self.workunits

    def workunit_read(self):
        print "WORKUNIT READ"
        res = map(lambda x: self.bfapp.read_object(endpoint='workunit', obj={'id': x}), self.workunits)
        res = filter(lambda x: x[0].description == '68b329da9893e34099c7d8ad5cb9c940', res)
        print res
        self.assertEqual(len(res), len(self.workunits))

    def workunit_delete(self):
        print "WORKUNIT DELETE"
        res = map(lambda x: self.bfapp.delete_object(endpoint='workunit', id=x)[0], self.workunits)
        res = filter(lambda x: "removed successfully." in x.deletionreport, res)
        print res
        self.assertEqual(len(res), len(self.workunits))

    def sample_save(self):
        print "SAVE SAMPLE"
        for sample_type in ['Biological Sample - Proteomics']:
            res = self.bfapp.save_object(endpoint='sample', obj={'name': "unit test - {}".format(sample_type),
                                                                   'projectid': 1000,
                                                                   'type' : sample_type,
                                                                   'samplingdate' : "2017-10-12",
                                                                   'groupingvar' : "A",
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940'
                                                                   })

            print res
            self.samples.append(res[0]._id)

    def sample_delete(self):
        print "SAMPLE DELETE"
        print self.samples
        res = map(lambda x: self.bfapp.delete_object(endpoint='sample', id=x)[0], self.samples)
        res = filter(lambda x: "removed successfully." in x.deletionreport, res)
        print res
        self.assertEqual(len(res), len(self.samples))

    def test_workunit(self):
        self.workunit_save()
        self.workunit_read()
        self.workunit_delete()

    def test_sample(self):
        self.sample_save()
        self.sample_delete()

if __name__ == '__main__':
    unittest.main()
