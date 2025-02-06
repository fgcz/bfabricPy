from __future__ import annotations

from copy import deepcopy
from typing import Any, overload


def sort_dict(d: dict) -> dict:
    """Returns a copy of the dictionary with items sorted by key.
    Affects how the dictionary appears, when mapped to a string.
    :param d:  A dictionary
    :return:   A dictionary with items sorted by key.
    """
    return dict(sorted(d.items()))


def _recursive_drop_empty(response_elem: list | dict) -> None:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a dictionary value is encountered, that is
      either an empty list or None, the key-value pair gets deleted from the dictionary
    :param response_elem: One of the sub-objects in the hierarchical storage of the response. Initially the root
    :return: Nothing
    """
    if isinstance(response_elem, list):
        for el in response_elem:
            _recursive_drop_empty(el)
    elif isinstance(response_elem, dict):
        keys_to_delete = []  # NOTE: Avoid deleting keys inside iterator, may break iterator
        for k, v in response_elem.items():
            if (v is None) or (isinstance(v, list) and len(v) == 0):
                keys_to_delete += [k]
            else:
                _recursive_drop_empty(v)
        for k in keys_to_delete:
            del response_elem[k]


@overload
def drop_empty_elements(response: list[dict[str, Any]], inplace: bool) -> list[dict[str, Any]]: ...


@overload
def drop_empty_elements(response: dict[str, Any], inplace: bool) -> dict[str, Any]: ...


def drop_empty_elements(response: list | dict, inplace: bool = True) -> list | dict:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a dictionary value is encountered, that is
      either an empty list or None, the key-value pair gets deleted from the dictionary
    :param response:  A parsed query response, consisting of nested lists, dicts and basic types (int, str)
    :param inplace:   If true, will return nothing and edit the argument. Otherwise, will preserve the argument
        and return an edited copy
    :return: An edited response, depending on `inplace`
    """
    response_filtered = deepcopy(response) if not inplace else response
    _recursive_drop_empty(response_filtered)
    return response_filtered


def _recursive_map_keys(response_elem: list | dict, keymap: dict) -> None:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a dictionary key is found for which
       the mapping is requested, that the key is renamed to the corresponding mapped one
    :param response_elem: One of the sub-objects in the hierarchical storage of the response. Initially the root
    :param keymap:    A map containing key names that should be renamed, and values - the new names.
    :return: Nothing
    """
    if isinstance(response_elem, list):
        for el in response_elem:
            _recursive_map_keys(el, keymap)
    elif isinstance(response_elem, dict):
        keys_to_delete = []  # NOTE: Avoid deleting keys inside iterator, may break iterator
        for k, v in response_elem.items():
            _recursive_map_keys(v, keymap)
            if k in keymap:
                keys_to_delete += [k]

        for k in keys_to_delete:
            response_elem[keymap[k]] = response_elem[k]  # Copy old value to the new key
            del response_elem[k]  # Delete old key


def map_element_keys(response: list | dict, keymap: dict, inplace: bool = True) -> list | dict:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a dictionary key is found for which
       the mapping is requested, that the key is renamed to the corresponding mapped one
    :param response:  A parsed query response, consisting of nested lists, dicts and basic types (int, str)
    :param keymap:    A map containing key names that should be renamed, and values - the new names.
    :param inplace:   If true, will return nothing and edit the argument. Otherwise, will preserve the argument
        and return an edited copy
    :return: The edited response (original or copy, depending on inplace)
    """
    response_filtered = deepcopy(response) if not inplace else response
    _recursive_map_keys(response_filtered, keymap)
    return response_filtered


def _recursive_sort_dicts_by_key(response_elem: list | dict) -> None:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a nested dictionary is found, it is sorted
    by key by converting into OrderedDict and back
    :param response_elem: One of the sub-objects in the hierarchical storage of the response. Initially the root
    :return: Nothing
    """
    if isinstance(response_elem, list):
        for idx, el in enumerate(response_elem):
            if isinstance(el, dict):
                response_elem[idx] = sort_dict(el)
            _recursive_sort_dicts_by_key(el)
    elif isinstance(response_elem, dict):
        for k, v in response_elem.items():
            if isinstance(v, dict):
                response_elem[k] = sort_dict(v)
            _recursive_sort_dicts_by_key(v)


def sort_dicts_by_key(response: list | dict, inplace: bool = True) -> list | dict | None:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a nested dictionary is found, it is sorted
       by key by converting into OrderedDict and back
    :param response:  A parsed query response, consisting of nested lists, dicts and basic types (int, str)
    :param inplace:   If true, will return nothing and edit the argument. Otherwise, will preserve the argument
        and return an edited copy
    :return: Nothing, or an edited response, depending on `inplace`
    """
    response_filtered = deepcopy(response) if not inplace else response
    _recursive_sort_dicts_by_key(response_filtered)
    return response_filtered


def clean_result(result: dict, drop_underscores_suds: bool = True, sort_keys: bool = False) -> dict:
    """
    :param result: the response dictionary to clean
    :param drop_underscores_suds: if True, the keys of the dictionaries in the response will have leading
        underscores removed in some cases (relevant for SUDS)
    :param sort_keys: the keys of the dictionaries in the response will be sorted (recursively)
    """
    result = deepcopy(result)
    if drop_underscores_suds:
        map_element_keys(
            result,
            {"_id": "id", "_classname": "classname", "_projectid": "projectid"},
            inplace=True,
        )
    if sort_keys:
        sort_dicts_by_key(result, inplace=True)

    return result
