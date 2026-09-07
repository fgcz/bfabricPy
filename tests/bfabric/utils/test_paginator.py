import math
import unittest

import pytest

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
        # No pages are requested, so the caller never applies init_offset; its value (100 % 3)
        # is unobservable here. Asserted only to pin that the offset formula is independent of
        # n_item_return_max.
        self.assertEqual(1, init_offset)

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


def _retained_window(n_items: int, n_item_per_page: int, offset: int, max_results: int | None) -> list[int]:
    """Reconstruct which items ``Bfabric.read`` retains, driving the real page math.

    Mirrors the consumption loop in ``Bfabric.read``: request the computed pages, slice the
    first one at ``initial_offset``, concatenate, then truncate to ``max_results``. Items are
    represented by their 0-based global index, so the result should equal the half-open window
    ``[offset, offset + max_results)``.
    """
    n_page_total = math.ceil(n_items / n_item_per_page)
    pages, initial_offset = paginator.compute_requested_pages(
        n_page_total=n_page_total,
        n_item_per_page=n_item_per_page,
        n_item_offset=offset,
        n_item_return_max=max_results,
    )
    retained: list[int] = []
    page_offset = initial_offset
    for page in pages:
        page_items = list(range((page - 1) * n_item_per_page, min(page * n_item_per_page, n_items)))
        retained += page_items[page_offset:]
        page_offset = 0
    return retained if max_results is None else retained[:max_results]


# Regression matrix for the offset/max_results interaction. Before the fix, initial_offset used
# min(n_item_offset, n_item_return_max), silently shifting the window whenever max_results < offset
# and the two differ modulo the page size (e.g. offset=100, max=10 with a page size of 50). The
# pre-existing tests never varied both parameters at once, so that quadrant shipped untested.
@pytest.mark.parametrize("n_item_per_page", [3, 50, 100])
@pytest.mark.parametrize(
    ("offset", "max_results"),
    [
        (0, None),  # everything
        (0, 10),  # only max
        (10, None),  # only offset
        (10, 5),  # the broken quadrant: max < offset
        (100, 10),  # broken quadrant, larger
        (250, 100),  # broken quadrant, page-crossing
        (95, 10),  # window straddles a page boundary
        (50, 200),  # offset < max
        (999, 10),  # offset beyond the end -> empty window
    ],
)
def test_read_window_matches_offset_and_max(n_item_per_page: int, offset: int, max_results: int | None) -> None:
    n_items = 1000
    full = list(range(n_items))
    expected = full[offset:] if max_results is None else full[offset : offset + max_results]
    assert _retained_window(n_items, n_item_per_page, offset, max_results) == expected


if __name__ == "__main__":
    unittest.main(verbosity=2)
