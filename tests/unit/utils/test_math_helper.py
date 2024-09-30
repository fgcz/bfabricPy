import unittest

import bfabric.utils.math_helper as math_helper


class BfabricTestMath(unittest.TestCase):
    def test_integer_division(self):
        # Main purpose of dictionary sorting is that they appear consistent when printed
        self.assertEqual(math_helper.div_int_ceil(120, 100), 2)
        self.assertEqual(math_helper.div_int_ceil(200, 100), 2)
        self.assertEqual(math_helper.div_int_ceil(245, 100), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
