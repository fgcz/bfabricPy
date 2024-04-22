import json
import os
import unittest

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth


class BfabricTestRead(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BfabricTestRead, self).__init__(*args, **kwargs)

        # Load ground truth
        path = os.path.join(os.path.dirname(__file__), "groundtruth.json")
        with open(path) as json_file:
            self.ground_truth = json.load(json_file)

        # Load config and authentification
        self.config, self.auth = get_system_auth()

        # Init the engines
        self.bfZeep = Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.ZEEP)
        self.bfSuds = Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.SUDS)

    def read(self, bf: Bfabric, endpoint: str):
        """Executes read queries for `endpoint` and compares results with ground truth."""
        self.assertIn(endpoint, self.ground_truth)
        for query, ground_truth in self.ground_truth[endpoint]:
            res = bf.read(endpoint=endpoint, obj=query).to_list_dict()

            # print(query, res)

            self.assertEqual(len(res), 1)  # Expecting only one query result in all cases
            for gt_attr, gt_value in ground_truth.items():
                self.assertEqual(str(gt_value), str(res[0][gt_attr]))

    def _test_empty_project(self, bf: Bfabric):
        res = bf.read(endpoint="project", obj={"name": "this project does not exist"}).to_list_dict()
        self.assertEqual(res, [])

    def test_user(self):
        self.read(self.bfSuds, "user")
        self.read(self.bfZeep, "user")

    def test_container(self):
        self.read(self.bfSuds, "container")
        self.read(self.bfZeep, "container")

    def test_project(self):
        self.read(self.bfSuds, "project")
        # self.read(self.bfZeep, "project")  # FIXME: Zeep does not parse name correctly for project queries

    def test_project_when_not_exists(self):
        self._test_empty_project(self.bfZeep)
        self._test_empty_project(self.bfSuds)

    def test_application(self):
        self.read(self.bfSuds, "application")
        self.read(self.bfZeep, "application")

    def test_sample(self):
        self.read(self.bfSuds, "sample")
        self.read(self.bfZeep, "sample")

    def test_workunit(self):
        self.read(self.bfSuds, "workunit")
        self.read(self.bfZeep, "workunit")

    def test_resource(self):
        self.read(self.bfSuds, "resource")
        self.read(self.bfZeep, "resource")

    def test_executable(self):
        self.read(self.bfSuds, "executable")
        self.read(self.bfZeep, "executable")

    def test_annotation(self):
        self.read(self.bfSuds, "annotation")
        self.read(self.bfZeep, "annotation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
