import logging
import unittest

from bfabric.results.result_container import ResultContainer


class BfabricTestResultContainer(unittest.TestCase):
    def setUp(self):
        self.res1 = ResultContainer([1, 2, 3], total_pages_api=1)
        self.res2 = ResultContainer([4, 5], total_pages_api=1)
        self.res_with_empty = ResultContainer([{"a": None, "b": 1, "c": []}, {"a": 2, "b": 3, "c": None}])

    def test_str(self):
        self.assertEqual("[1, 2, 3]", str(self.res1))
        self.assertEqual("[4, 5]", str(self.res2))

    def test_repr(self):
        self.assertEqual("[1, 2, 3]", str(self.res1))
        self.assertEqual("[4, 5]", str(self.res2))

    def test_len(self):
        self.assertEqual(3, len(self.res1))
        self.assertEqual(2, len(self.res2))

    def test_getitem(self):
        self.assertEqual(3, self.res1[2])
        self.assertEqual(4, self.res2[0])

    def test_get_first_n_results_when_available(self):
        res3 = self.res1.get_first_n_results(2)
        self.assertEqual(2, len(res3))
        self.assertEqual([1, 2], res3.results)

    def test_get_first_n_results_when_not_available(self):
        res3 = self.res1.get_first_n_results(4)
        self.assertEqual(3, len(res3))
        self.assertEqual([1, 2, 3], res3.results)

    def test_get_first_n_results_when_none(self):
        res3 = self.res1.get_first_n_results(None)
        self.assertEqual(3, len(res3))
        self.assertEqual([1, 2, 3], res3.results)

    def test_assert_success_when_success(self):
        self.res1.assert_success()

    def test_assert_success_when_error(self):
        self.res1.errors.append("MockedError")
        with self.assertRaises(RuntimeError) as error:
            self.res1.assert_success()
        self.assertEqual("('Query was not successful', ['MockedError'])", str(error.exception))

    def test_extend_when_same_lengths(self):
        res1 = ResultContainer([{"a": 1}, {"a": 2}], total_pages_api=5)
        res2 = ResultContainer([{"b": 3}, {"b": 4}], total_pages_api=5)
        res1.extend(res2)
        self.assertEqual(4, len(res1))
        self.assertEqual([{"a": 1}, {"a": 2}, {"b": 3}, {"b": 4}], res1.results)
        self.assertEqual(5, res1.total_pages_api)

    def test_extend_when_different_lengths(self):
        res3 = ResultContainer(
            list(range(200, 400)),
            total_pages_api=2,
        )
        with self.assertLogs(level=logging.WARNING) as error:
            res3.extend(self.res1)

        self.assertEqual(203, len(res3))
        self.assertEqual(list(range(200, 400)) + [1, 2, 3], res3.results)
        self.assertEqual(2, res3.total_pages_api)
        self.assertIn("Results observed with different total pages counts: 2 != 1", str(error))

    def test_to_list_dict_when_not_drop_empty(self):
        expected = [{"a": None, "b": 1, "c": []}, {"a": 2, "b": 3, "c": None}]
        with self.subTest(case="default"):
            self.assertListEqual(expected, self.res_with_empty.to_list_dict())
        with self.subTest(case="explicit"):
            self.assertListEqual(expected, self.res_with_empty.to_list_dict(drop_empty=False))

    def test_to_list_dict_when_drop_empty(self):
        expected = [{"b": 1}, {"a": 2, "b": 3}]
        self.assertListEqual(expected, self.res_with_empty.to_list_dict(drop_empty=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
