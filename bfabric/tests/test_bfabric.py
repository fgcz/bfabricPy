import unittest
from bfabric import Bfabric

"""
ssh localhost "cat > /tmp/bb.py && /usr/bin/python /tmp/bb.py" < PycharmProjects/untitled/bfabric_wsdl.py 
"""
class MyTestCase(unittest.TestCase):
    bfapp = Bfabric()

    workunits = []


    def workunit_save(self):
        print "SAVE"
        for wname in ['test1', 'test2', 'test3']:
            res = self.bfapp.save_object(endpoint='workunit', obj={'name': wname,
                                                                   'projectid': 1000,
                                                                   'description': '68b329da9893e34099c7d8ad5cb9c940',
                                                                   'applicationid': 217
                                                                   })

            self.workunits.append(res[0]._id)
        print self.workunits

    def workunit_read(self):
        print "READ"
        res = map(lambda x: self.bfapp.read_object(endpoint='workunit', obj={'id': x}), self.workunits)
        print res
        self.assertEqual(len(res), len(self.workunits))

    def workunit_delete(self):
        print "DELETE"
        res = map(lambda x: self.bfapp.delete_object(endpoint='workunit', id=x), self.workunits)
        print res
        self.assertEqual(len(res), len(self.workunits))

    def test_workunit(self):
        self.workunit_save()
        self.workunit_read()
        self.workunit_delete()

        # print self.bfapp.read_object(endpoint='workunit', obj={'description': '68b329da9893e34099c7d8ad5cb9c940'})



if __name__ == '__main__':
    unittest.main()
