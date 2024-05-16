import json
import os
import unittest

from bfabric import Bfabric, BfabricAPIEngineType
from bfabric.experimental.multi_query import MultiQuery


class BfabricTestMulti(unittest.TestCase):
    def setUp(self, *args, **kwargs):
        # Load ground truth
        path = os.path.join(os.path.dirname(__file__), "groundtruth.json")
        with open(path) as json_file:
            self.ground_truth = json.load(json_file)

        # Create clients
        self.clients = {
            "zeep": Bfabric.from_config("TEST", engine=BfabricAPIEngineType.ZEEP),
            "suds": Bfabric.from_config("TEST", engine=BfabricAPIEngineType.SUDS),
        }

    def _test_multi_read_delete(self, engine: str):
        """
        Create many workunits
        * Test if reading multiple of those workunits works
        * Test if exists on multiple workunits works
        * Test if deleting multiple workunits works
        """
        with self.subTest(engine=engine):
            bf: Bfabric = self.clients[engine]
            mq = MultiQuery(bf)

            # 1. Create a bunch of workunits
            #   Note: we crate more than 100, to make sure pagination works correctly
            n_units = 105
            workunit_ids = []
            for i in range(n_units):
                query = {"name": "fancy_workunit_"+str(i), "applicationid": 2, "description": "is very fancy", "containerid": 3000}
                res = bf.save("workunit", query).to_list_dict()
                self.assertEqual(len(res), 1)
                self.assertIn("id", res[0])
                workunit_ids += [res[0]['id']]


            #2. TODO: Make sure that the results are indeed read correctly, not just read
            res = mq.read_multi('workunit', {}, 'id', workunit_ids, return_id_only=True)

            #3. Check if correct ones exist and fake one does not
            res = mq.exists_multi('workunit', 'id', workunit_ids + [10101010101010])
            self.assertEqual(len(res), n_units + 1)
            self.assertTrue(all(res[:n_units]))
            self.assertFalse(res[n_units])

            # 4. Delete all workunits at the same time
            res = mq.delete_multi('workunit', workunit_ids)
            self.assertEqual(len(res), n_units)


    # TODO: Implement me
    def _test_multi_read_complex(self, engine: str):
        """
        The main idea is to test how BFabric API behaves in case it is given multiple of the same field,
        where for each field there is more than one result.
        * e.g. for 'id' there is only one result, but for 'status there could be many'
        * a test could try to get all files with {'status': ['archived', 'archiving']} that have been recently created,
           such that in total there is more than 100 results.
        """
        pass

    def test_multi_delete(self):
        self._test_multi_read_delete("suds")
        self._test_multi_read_delete("zeep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
