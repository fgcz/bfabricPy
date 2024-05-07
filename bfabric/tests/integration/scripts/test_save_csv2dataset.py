from __future__ import annotations
import time
import unittest
import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from bfabric.bfabric2 import Bfabric
from bfabric.scripts.bfabric_save_csv2dataset import bfabric_save_csv2dataset
from bfabric.tests.integration.integration_test_helper import DeleteEntities


class TestSaveCsv2Dataset(unittest.TestCase):
    def setUp(self):
        self.mock_client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.created_entities = []
        self.addCleanup(DeleteEntities(self.mock_client, self.created_entities))

        self.sample_data = pl.DataFrame(
            [
                {
                    "Normal": "just a normal string",
                    "Comma": "contains,some,commas,,,",
                    "Backslash": "testing\\backslash/support",
                    "Apostrophe": 'Lot\'s"of"apostrophes',
                }
            ]
        )

    def test_save_csv2dataset(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            sample_file = work_dir / "sample_table.csv"
            self.sample_data.write_csv(sample_file)

            bfabric_save_csv2dataset(
                self.mock_client,
                csv_file=sample_file,
                dataset_name=f"test_dataset {timestamp}",
                container_id=3000,
                workunit_id=None,
                sep=",",
                has_header=True,
            )

        # check the result
        time.sleep(1)
        response = self.mock_client.read("dataset", {"name": f"test_dataset {timestamp}"}).to_list_dict()[0]
        self.created_entities.append(("dataset", response["id"]))

        expected_attribute = [
            {"name": "Normal", "position": "1", "type": "String"},
            {"name": "Comma", "position": "2", "type": "String"},
            {"name": "Backslash", "position": "3", "type": "String"},
            {"name": "Apostrophe", "position": "4", "type": "String"},
        ]
        self.assertListEqual(expected_attribute, response["attribute"])

        expected_item = [
            {
                "field": [
                    {"attributeposition": "1", "value": "just a normal string"},
                    {"attributeposition": "2", "value": "contains,some,commas,,,"},
                    {"attributeposition": "3", "value": "testing\\backslash/support"},
                    {"attributeposition": "4", "value": 'Lot\'s"of"apostrophes'},
                ],
                "position": "1",
            }
        ]
        self.assertListEqual(expected_item, response["item"])

    def test_save_csv2dataset_no_header(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            sample_file = work_dir / "sample_table.csv"
            self.sample_data.write_csv(sample_file, include_header=False)

            bfabric_save_csv2dataset(
                self.mock_client,
                csv_file=sample_file,
                dataset_name=f"test_dataset {timestamp}",
                container_id=3000,
                workunit_id=None,
                sep=",",
                has_header=False,
            )

        # check the result
        time.sleep(1)
        response = self.mock_client.read("dataset", {"name": f"test_dataset {timestamp}"}).to_list_dict()[0]
        self.created_entities.append(("dataset", response["id"]))

        expected_attribute = [
            {"name": "Column_1", "position": "1", "type": "String"},
            {"name": "Column_2", "position": "2", "type": "String"},
            {"name": "Column_3", "position": "3", "type": "String"},
            {"name": "Column_4", "position": "4", "type": "String"},
        ]
        self.assertListEqual(expected_attribute, response["attribute"])

        expected_item = [
            {
                "field": [
                    {"attributeposition": "1", "value": "just a normal string"},
                    {"attributeposition": "2", "value": "contains,some,commas,,,"},
                    {"attributeposition": "3", "value": "testing\\backslash/support"},
                    {"attributeposition": "4", "value": 'Lot\'s"of"apostrophes'},
                ],
                "position": "1",
            }
        ]
        self.assertListEqual(expected_item, response["item"])


if __name__ == "__main__":
    unittest.main()
