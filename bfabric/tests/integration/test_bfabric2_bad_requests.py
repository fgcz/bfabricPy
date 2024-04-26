import json
import os
import unittest

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth
from bfabric.src.errors import BfabricRequestError


class BfabricTestBadRequest(unittest.TestCase):
    def setUp(self):
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

    def _test_non_existing_read(self, engine_name: str):
        # NOTE: Currently a bad read request simply returns no matches, but does not throw errors
        res = self.clients[engine_name].read('user', {'id': 'cat'}).to_list_dict()
        self.assertEqual([], res)

    def _test_forbidden_save(self, engine_name: str):
        # Test what happens if we save to an endpoint that does not accept saving
        self.assertRaises(
            BfabricRequestError,
            self.clients[engine_name].save,
            'project',
            {'name': 'TheForbiddenPlan'}
        )

    def _test_wrong_delete(self, engine_name: str):
        self.assertRaises(
            RuntimeError,
            self.clients[engine_name].delete,
            'workunit',
            101010101010101
        )

    def test_non_existing_read_when_suds(self):
        self._test_non_existing_read("suds")

    def test_non_existing_read_when_zeep(self):
        self._test_non_existing_read("zeep")

    def test_forbidden_save_when_suds(self):
        self._test_forbidden_save("suds")

    def test_forbidden_save_when_zeep(self):
        self._test_forbidden_save("zeep")

    def test_wrong_delete_when_suds(self):
        self._test_wrong_delete("suds")

    def test_wrong_delete_when_zeep(self):
        self._test_wrong_delete("zeep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
