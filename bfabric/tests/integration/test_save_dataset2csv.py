import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from bfabric.bfabric2 import Bfabric
from bfabric.scripts.bfabric_save_dataset2csv import bfabric_save_dataset2csv


class TestSaveDataset2Csv(unittest.TestCase):
    def setUp(self):
        self.mock_client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.dataset_id = 46184

    def test_save_dataset2csv(self):
        with TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            bfabric_save_dataset2csv(self.mock_client, self.dataset_id, out_dir, sep=",")

            expected_lines = [
                r"Normal,Comma,Backslash,Apostrophe",
                r"""just a normal string,"contains,some,commas,,,",testing\backslash/support,"Lot's""of""apostrophes"""
                '"',
            ]

            out_file = out_dir / "dataset.csv"
            actual_lines = out_file.read_text().splitlines()

            self.assertListEqual(expected_lines, actual_lines)

            df = pd.read_csv(out_file)
            expected_df = pd.DataFrame(
                [
                    {
                        "Normal": "just a normal string",
                        "Comma": "contains,some,commas,,,",
                        "Backslash": "testing\\backslash/support",
                        "Apostrophe": 'Lot\'s"of"apostrophes',
                    }
                ]
            )
            pd.testing.assert_frame_equal(expected_df, df)


if __name__ == "__main__":
    unittest.main()
