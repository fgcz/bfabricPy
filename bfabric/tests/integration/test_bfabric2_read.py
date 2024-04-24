import json
import os
import unittest

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth


class BfabricTestRead(unittest.TestCase):
    def setUp(self, *args, **kwargs):
        # Load ground truth
        path = os.path.join(os.path.dirname(__file__), "groundtruth.json")
        with open(path) as json_file:
            self.ground_truth = json.load(json_file)

        # Load config and authentication
        self.config, self.auth = get_system_auth(config_env="TEST")

        # Init the engines
        self.clients = {
            "zeep": Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.ZEEP),
            "suds": Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.SUDS)
        }

    def read(self, engine: str, endpoint: str):
        """Executes read queries for `endpoint` and compares results with ground truth."""
        with self.subTest(engine=engine):
            bf = self.clients[engine]
            self.assertIn(endpoint, self.ground_truth)
            for query, ground_truth in self.ground_truth[endpoint]:
                res = bf.read(endpoint=endpoint, obj=query).to_list_dict()

                # print(query, res)

                self.assertEqual(len(res), 1)  # Expecting only one query result in all cases
                for gt_attr, gt_value in ground_truth.items():
                    self.assertEqual(str(gt_value), str(res[0][gt_attr]))

    def _test_empty_project(self, engine: str):
        with self.subTest(engine=engine):
            bf = self.clients[engine]
            res = bf.read(endpoint="project", obj={"name": "this project does not exist"}).to_list_dict()
            self.assertEqual(res, [])

    def test_user(self):
        self.read("suds", "user")
        self.read("zeep", "user")

    def test_container(self):
        self.read("suds", "container")
        self.read("zeep", "container")

    def test_project(self):
        self.read("suds", "project")
        # self.read("zeep", "project")  # FIXME: Zeep does not parse name correctly for project queries

    def test_project_when_not_exists(self):
        self._test_empty_project("zeep")
        self._test_empty_project("suds")

    def test_application(self):
        self.read("suds", "application")
        self.read("zeep", "application")

    def test_sample(self):
        self.read("suds", "sample")
        self.read("zeep", "sample")

    def test_workunit(self):
        self.read("suds", "workunit")
        self.read("zeep", "workunit")

    def test_resource(self):
        self.read("suds", "resource")
        self.read("zeep", "resource")

    def test_executable(self):
        self.read("suds", "executable")
        self.read("zeep", "executable")

    def test_annotation(self):
        self.read("suds", "annotation")
        self.read("zeep", "annotation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
