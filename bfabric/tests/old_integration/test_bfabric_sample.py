#!/usr/bin/env python3

"""
unittest by <cp@fgcz.ethz.ch>
"""

import unittest
from bfabric.bfabric_legacy import BfabricLegacy

"""
ssh localhost "cat > /tmp/bb.py && /usr/bin/python /tmp/bb.py" < PycharmProjects/untitled/bfabric_wsdl.py 
"""


class BfabricTestCase(unittest.TestCase):

    workunits = []
    samples = []

    bfapp = BfabricLegacy(verbose=True)

    def sample_save(self):
        print("SAVE SAMPLE")
        sample_type = "Biological Sample - Proteomics"
        species = "n/a"
        for name in [1, 2, 3]:
            res = self.bfapp.save_object(
                endpoint="sample",
                obj={
                    "name": f"unit test - #{name} - {sample_type}",
                    "containerid": 3000,
                    "type": sample_type,
                    "species": species,
                    "samplingdate": "2017-10-12",
                    "groupingvar": "A",
                    "description": "68b329da9893e34099c7d8ad5cb9c940",
                },
            )

            for i in res:
                print(i)
            # self.samples.append(res[0].id)

    def sample_delete(self):
        print("SAMPLE DELETE")
        print(self.samples)
        res = [self.bfapp.delete_object(endpoint="sample", id=x)[0] for x in self.samples]
        res = [x for x in res if "removed successfully." in x.deletionreport]
        print(res)
        self.assertEqual(len(res), len(self.samples))

    def test_sample(self):
        self.sample_save()
        # self.sample_delete()


if __name__ == "__main__":
    unittest.main()
