import contextlib
import json
import unittest
from io import StringIO

import yaml

from bfabric import Bfabric
from bfabric.scripts.bfabric_read import bfabric_read
from bfabric.tests.integration.integration_test_helper import DeleteEntities


class TestRead(unittest.TestCase):
    def setUp(self):
        self.client = Bfabric.from_config(config_env="TEST")
        self.delete_entities = DeleteEntities(client=self.client, created_entities=[])
        self.addCleanup(self.delete_entities)

        self.example = {"endpoint": "resource"}

    def test_read_json(self):
        out = StringIO()
        with contextlib.redirect_stdout(out):
            bfabric_read(
                client=self.client, endpoint=self.example["endpoint"], attribute=None, value=None, output_format="json"
            )
        parsed = json.loads(out.getvalue())
        self.assertEqual(100, len(parsed))

    def test_read_yaml(self):
        out = StringIO()
        with contextlib.redirect_stdout(out):
            bfabric_read(
                client=self.client, endpoint=self.example["endpoint"], attribute=None, value=None, output_format="yaml"
            )
        parsed = yaml.safe_load(out.getvalue())
        self.assertEqual(100, len(parsed))


if __name__ == "__main__":
    unittest.main()
