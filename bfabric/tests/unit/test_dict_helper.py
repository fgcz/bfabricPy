import unittest

import bfabric.src.dict_helper as dict_helper


class BfabricTestCase(unittest.TestCase):
    def test_sort_dict(self):
        # Main purpose of dictionary sorting is that they appear consistent when printed
        d = {'c': 5, 'b': 10}
        d_sorted = dict_helper.sort_dict(d)
        self.assertEqual(str(d_sorted), "{'b': 10, 'c': 5}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
