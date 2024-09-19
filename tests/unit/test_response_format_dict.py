import unittest

import bfabric.results.response_format_dict as response_format_dict


class BfabricTestResponseFormatDict(unittest.TestCase):
    def test_drop_empty_elements(self):
        # Should delete all hierarchical instances of key-value pairs, where value is None or empty dict
        input_list_dict = [{"a": [], "b": [1, {"aa": 14, "gg": None}], "c": []}, {"zz": None, "uu": "cat"}]
        target_list_dict = [{"b": [1, {"aa": 14}]}, {"uu": "cat"}]

        output_list_dict = response_format_dict.drop_empty_elements(input_list_dict, inplace=False)
        self.assertEqual(output_list_dict, target_list_dict)

    def test_map_element_keys(self):
        # Main use is to delete underscores in specific keys
        input_list_dict = [{"a": [], "b": [1, {"_aa": 14, "gg": None}], "c": []}, {"zz": None, "uu": "cat"}]
        target_list_dict = [{"a": [], "b": [1, {"aa": 14, "gg": None}], "c": []}, {"zz": None, "uu": "cat"}]

        output_list_dict = response_format_dict.map_element_keys(input_list_dict, {"_aa": "aa"}, inplace=False)
        self.assertEqual(output_list_dict, target_list_dict)

    def test_sort_dicts_by_key(self):
        # NOTE: The main purpose of sorting is to ensure consistent string representation
        input_list_dict = [{"b": 1, "a": 2, "c": 3}, {"dog": 25, "cat": [1, 2, 3]}]
        target_list_dict = [{"a": 2, "b": 1, "c": 3}, {"cat": [1, 2, 3], "dog": 25}]

        output_list_dict = response_format_dict.sort_dicts_by_key(input_list_dict, inplace=False)
        self.assertEqual(str(output_list_dict), str(target_list_dict))

    def test_clean_result(self):
        result_input = [{"b": 1, "a": 2, "_id": 3}, {"b": 4, "_id": 5, "a": 6}]
        cleaned = response_format_dict.clean_result(result_input, drop_underscores_suds=True, sort_keys=True)
        self.assertEqual(repr([{"a": 2, "b": 1, "id": 3}, {"a": 6, "b": 4, "id": 5}]), repr(cleaned))
        self.assertEqual(
            repr([{"b": 1, "a": 2, "_id": 3}, {"b": 4, "_id": 5, "a": 6}]),
            repr(result_input),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
