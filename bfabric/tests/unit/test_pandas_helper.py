import unittest
import numpy as np

import bfabric.results.pandas_helper as pandas_helper


class BfabricTestPandasHelper(unittest.TestCase):
    def test_list_dict_to_df(self):
        # Main purpose of dictionary sorting is that they appear consistent when printed
        example_list_dict = [
            {"cat": 1, "dog": 2},
            {"cat": 3, "rat": ["a", "b"]},
            {"rat": 5},
            {"cat": 1, "dog": 2, "rat": 7},
        ]

        df = pandas_helper.list_dict_to_df(example_list_dict)
        self.assertEqual(list(df.columns), ["cat", "dog", "rat"])
        np.testing.assert_equal(list(df["cat"]), [1, 3, np.nan, 1])
        np.testing.assert_equal(list(df["dog"]), [2, np.nan, np.nan, 2])
        np.testing.assert_equal(list(df["rat"]), [np.nan, "['a', 'b']", 5, 7])


if __name__ == "__main__":
    unittest.main(verbosity=2)
