#!/usr/bin/env python3

"""
unittest by <cp@fgcz.ethz.ch>
2019-09-11
"""
import json
import os
import unittest

import bfabric
import bfabric.bfabric_legacy


class BfabricTestCaseReadEndPoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "groundtruth.json")
        with open(path) as json_file:
            cls.ground_truth = json.load(json_file)
        cls.bfapp = bfabric.bfabric_legacy.Bfabric(verbose=False)

    def read(self, endpoint):
        """Executes read queries for `endpoint` and compares results with ground truth."""
        self.assertIn(endpoint, self.ground_truth)
        for query, ground_truth in self.ground_truth[endpoint]:
            res = self.bfapp.read_object(endpoint=endpoint, obj=query)
            for gt_attr, gt_value in ground_truth.items():
                with self.subTest(endpoint=endpoint, query=query):
                    # sort results for comparison by id
                    res = sorted(res, key=lambda x: x._id)

                    # cast all values to strings (i.e. ignoring int/float/string differences)
                    self.assertEqual(str(gt_value), str(res[0][gt_attr]))

    def test_user(self):
        self.read("user")

    def test_container(self):
        self.read("container")

    def test_project(self):
        self.read("project")

    def test_project_when_not_exists(self):
        res = self.bfapp.read_object(endpoint="project", obj={"name": "this project does not exist"})
        self.assertEqual(res, [])

    def test_application(self):
        self.read("application")

    def test_sample(self):
        self.read("sample")

    def test_workunit(self):
        self.read("workunit")

    def test_resource(self):
        self.read("resource")

    def test_executable(self):
        self.read("executable")

    def test_annotation(self):
        self.read("annotation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
