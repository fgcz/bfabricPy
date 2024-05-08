import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from bfabric.bfabric2 import Bfabric
from bfabric.scripts.bfabric_save_csv2dataset import bfabric_save_csv2dataset


class TestSaveCsv2Dataset(unittest.TestCase):
    def setUp(self):
        self.mock_client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.dataset_id = 46184

    def test_save_csv2dataset(self):
        data = pd.DataFrame(
            [
                {
                    "Normal": "just a normal string",
                    "Comma": "contains,some,commas,,,",
                    "Backslash": "testing\\backslash/support",
                    "Apostrophe": 'Lot\'s"of"apostrophes',
                }
            ]
        )
        timestamp = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            sample_file = work_dir / "sample_table.csv"
            data.to_csv(sample_file, index=False)
            bfabric_save_csv2dataset(
                self.mock_client,
                csv_file=sample_file,
                dataset_name=f"test_dataset {timestamp}",
                container_id=3000,
                workunit_id=None,
            )

        # check the result
        time.sleep(1)
        response = self.mock_client.read("dataset", {"name": f"test_dataset {timestamp}"}).to_list_dict()[0]

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

        self.mock_client.delete("dataset", response["id"])


if __name__ == "__main__":
    unittest.main()
