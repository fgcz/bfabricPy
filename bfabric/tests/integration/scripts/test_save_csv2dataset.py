from __future__ import annotations

import datetime
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from bfabric import Bfabric
from bfabric.scripts.bfabric_save_csv2dataset import bfabric_save_csv2dataset, check_for_invalid_characters
from bfabric.tests.integration.integration_test_helper import DeleteEntities


class TestSaveCsv2Dataset(unittest.TestCase):
    def setUp(self):
        self.client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.delete_entities = DeleteEntities(self.client)
        self.addCleanup(self.delete_entities)

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
                self.client,
                csv_file=sample_file,
                dataset_name=f"test_dataset {timestamp}",
                container_id=3000,
                workunit_id=None,
                sep=",",
                has_header=True,
                invalid_characters="",
            )

        # check the result
        time.sleep(1)
        response = self.client.read("dataset", {"name": f"test_dataset {timestamp}"}).to_list_dict()[0]
        self.delete_entities.register_entity(response)

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
                self.client,
                csv_file=sample_file,
                dataset_name=f"test_dataset {timestamp}",
                container_id=3000,
                workunit_id=None,
                sep=",",
                has_header=False,
                invalid_characters="",
            )

        # check the result
        time.sleep(1)
        response = self.client.read("dataset", {"name": f"test_dataset {timestamp}"}).to_list_dict()[0]
        self.delete_entities.register_entity(response)

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

    def test_save_csv2dataset_when_invalid_character(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            sample_file = work_dir / "sample_table.csv"
            self.sample_data.write_csv(sample_file)

            with self.assertRaises(RuntimeError) as error:
                bfabric_save_csv2dataset(
                    self.client,
                    csv_file=sample_file,
                    dataset_name=f"test_dataset {timestamp}",
                    container_id=3000,
                    workunit_id=None,
                    sep=",",
                    has_header=True,
                    invalid_characters=",",
                )

            self.assertEqual("Invalid characters found in columns: ['Comma']", str(error.exception))

        self.assertFalse(self.client.exists("dataset", "name", f"test_dataset {timestamp}"))

    def test_check_for_invalid_characters_when_good(self):
        example = pl.DataFrame({"col": ["good", "good", "good"], "numeric": [1, 2, 3]})
        check_for_invalid_characters(example, invalid_characters="+*")

    def test_check_for_invalid_characters_when_bad(self):
        example = pl.DataFrame({"col": ["good", "bad*", "good"], "numeric": [1, 2, 3]})
        with self.assertRaises(RuntimeError) as error:
            check_for_invalid_characters(example, invalid_characters="+*")
        self.assertIn("Invalid characters", str(error.exception))


if __name__ == "__main__":
    unittest.main()
