import unittest

import bfabric.utils.paginator as paginator


class BfabricTestBasicPagination(unittest.TestCase):
    def test_page_iter(self):
        # Main purpose of dictionary sorting is that they appear consistent when printed
        data = list(range(123))

        rez = list(paginator.page_iter(data, page_size=100))
        self.assertEqual(len(rez), 2)
        self.assertEqual(rez[0], list(range(100)))
        self.assertEqual(rez[1], list(range(100, 123)))

    def test_compute_requested_pages_when_no_offset(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=0, n_item_return_max=None
        )
        self.assertListEqual([1, 2, 3, 4, 5], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_offset_2(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=2, n_item_return_max=None
        )
        self.assertListEqual([1, 2, 3, 4, 5], pages)
        self.assertEqual(2, init_offset)

    def test_compute_requested_pages_when_offset_3(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=3, n_item_return_max=None
        )
        self.assertListEqual([2, 3, 4, 5], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_offset_4(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=4, n_item_return_max=None
        )
        self.assertListEqual([2, 3, 4, 5], pages)
        self.assertEqual(1, init_offset)

    def test_compute_requested_pages_when_offset_6(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=6, n_item_return_max=None
        )
        self.assertListEqual([3, 4, 5], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_offset_out_of_bounds(self):
        # TODO maybe it should yield an error?
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=100, n_item_return_max=None
        )
        self.assertListEqual([], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_max(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=0, n_item_return_max=10
        )
        self.assertListEqual([1, 2, 3, 4], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_max_9(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=0, n_item_return_max=9
        )
        self.assertListEqual([1, 2, 3], pages)
        self.assertEqual(0, init_offset)

    def test_compute_requested_pages_when_max_6(self):
        pages, init_offset = paginator.compute_requested_pages(
            n_page_total=5, n_item_per_page=3, n_item_offset=0, n_item_return_max=6
        )
        self.assertListEqual([1, 2], pages)
        self.assertEqual(0, init_offset)


if __name__ == "__main__":
    unittest.main(verbosity=2)
