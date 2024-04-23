import unittest

import bfabric.src.paginator as paginator


class BfabricTestBasicPagination(unittest.TestCase):
    def test_page_iter(self):
        # Main purpose of dictionary sorting is that they appear consistent when printed
        data = list(range(123))

        rez = list(paginator.page_iter(data, page_size=100))
        self.assertEqual(len(rez), 2)
        self.assertEqual(rez[0], list(range(100)))
        self.assertEqual(rez[1], list(range(100, 123)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
