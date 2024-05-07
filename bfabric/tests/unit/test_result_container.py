import unittest

import bfabric.src.result_container as result_container
from bfabric.src.errors import BfabricRequestError


class TestResultContainer(unittest.TestCase):
    def setUp(self):

        self.c1 = result_container.ResultContainer([1,2,3], total_pages_api=1,
                                                   result_type=result_container.BfabricResultType.LISTDICT)
        self.c2 = result_container.ResultContainer([4,5], total_pages_api=1,
                                                   result_type=result_container.BfabricResultType.LISTDICT)

    def test_str_repr(self):
        self.assertEqual(str(self.c1), "[1, 2, 3]")
        self.assertEqual(str(self.c2), "[4, 5]")

        self.assertEqual(repr(self.c1), "[1, 2, 3]")
        self.assertEqual(repr(self.c2), "[4, 5]")

    def test_len(self):
        self.assertEqual(len(self.c1), 3)
        self.assertEqual(len(self.c2), 2)

    def test_is_success_when_success(self):
        self.assertTrue(self.c1.is_success)

    def test_is_success_when_error(self):
        self.c1.errors.append(BfabricRequestError("error"))
        self.assertFalse(self.c1.is_success)

    def test_assert_success_when_success(self):
        self.c1.assert_success()

    def test_assert_success_when_error(self):
        self.c1.errors.append(BfabricRequestError("a descriptive error message"))
        with self.assertRaises(RuntimeError) as error:
            self.c1.assert_success()
        self.assertIn("a descriptive error message", str(error.exception))

    def test_get_item(self):
        self.assertEqual(self.c1[2], 3)
        self.assertEqual(self.c2[0], 4)

    def test_append(self):
        c3 = result_container.ResultContainer(list(range(200, 400)), total_pages_api=2,
                                              result_type=result_container.BfabricResultType.LISTDICT)
        c3.extend(self.c1)

        self.assertEqual(len(c3), 203)
        self.assertEqual(c3.results, list(range(200, 400)) + [1,2,3])
        self.assertEqual(c3.total_pages_api, 3)

    def test_to_list_dict(self):
        # NOTE: For LISTDICT format, the conversion to listdict does nothing
        self.assertEqual(self.c1.to_list_dict(), self.c1.results)

if __name__ == "__main__":
    unittest.main(verbosity=2)
