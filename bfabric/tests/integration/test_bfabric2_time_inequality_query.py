import unittest
from datetime import datetime, timedelta


from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth


class BfabricTestTimeInequalityQuery(unittest.TestCase):
    def setUp(self):
        # Load config and authentication
        self.config, self.auth = get_system_auth(config_env="TEST")

        # Init the engines
        self.clients = {
            "zeep": Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.ZEEP),
            "suds": Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.SUDS),
        }

    def _test_created_before_after(self, engine: str):
        with self.subTest(engine=engine):
            n_resources = 50
            bf = self.clients[engine]

            # 0. Create a workunit
            query = {
                "name": "CatPetter9000",
                "applicationid": 1,
                "containerid": 3000,
                "description": "Best cat petter ever",
            }
            res = bf.save("workunit", query).to_list_dict()
            self.assertIsNotNone(res)
            self.assertEqual(1, len(res))
            self.assertIn("id", res[0])
            workunit_id = res[0]["id"]

            # 1. Create a bunch of resources
            resource_ids = []
            resource_created = []
            for i_resource in range(n_resources):
                query = {
                    "name": "kitten_" + str(i_resource),
                    # 'sampleid': 1,
                    "filechecksum": 0,
                    "relativepath": "/catpath/kitten_" + str(i_resource),
                    "size": 0,
                    "status": "pending",
                    "storageid": 1,
                    "workunitid": workunit_id,
                }

                res = bf.save("resource", query).to_list_dict()
                self.assertIsNotNone(res)
                self.assertEquals(len(res), 1)
                self.assertIn("id", res[0])
                self.assertIn("created", res[0])

                resource_ids += [res[0]["id"]]
                resource_created += [datetime.fromisoformat(res[0]["created"])]

            # 2. attempt to find the resources we just created by datetime
            # NOTE:
            query = {
                "workunitid": workunit_id,
                "createdbefore": str(max(resource_created) + timedelta(seconds=1)),
                "createdafter": str(min(resource_created)),
            }
            results = bf.read("resource", query, return_id_only=True).to_list_dict()

            # 3. delete all created resources. Do this before test not to leave undeleted resources behind if possible
            bf.delete("resource", resource_ids)
            bf.delete("workunit", workunit_id)

            # 4. Check that the found resources are the ones we created
            # NOTE: We might find more resources, if somebody created resources at the same time as us
            #   Hence, we are testing for a subset, not an exact match
            resource_ids_found = [r["id"] for r in results]
            isSubset = set(resource_ids).issubset(set(resource_ids_found))
            # if not isSubset:
            #     print(min(resource_ids), max(resource_ids),  set(resource_ids) - set(resource_ids_found), set(resource_ids_found) - set(resource_ids))

            self.assertTrue(isSubset)

    def test_created(self):
        self._test_created_before_after("suds")
        self._test_created_before_after("zeep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
