from typing import Optional, Union
from copy import deepcopy


def _recursive_drop_empty(response_elem: Union[list, dict]) -> None:
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

def drop_empty_response_elements(response: Union[list, dict], inplace: bool = True) -> Optional[Union[list, dict]]:
    """
    Iterates over all nested lists, dictionaries and basic values. Whenever a dictionary value is encountered, that is
      either an empty list or None, the key-value pair gets deleted from the dictionary
    :param response:  A parsed query response, consisting of nested lists, dicts and basic types (int, str)
    :param inplace:   If true, will return nothing and edit the argument. Otherwise, will preserve the argument
        and return an edited copy
    :return: Nothing, or an edited response, depending on `inplace`
    """
    response_filtered = deepcopy(response) if not inplace else response
    _recursive_drop_empty(response_filtered)
    return response_filtered

def _recursive_map_keys(response_elem, keymap: dict) -> None:
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
            if k in keymap.keys():
                keys_to_delete += [k]

        for k in keys_to_delete:
            response_elem[keymap[k]] = response_elem[k]  # Copy old value to the new key
            del response_elem[k]                             # Delete old key

def map_response_element_keys(response: Union[list, dict], keymap: dict,
                              inplace: bool = True) -> Union[list, dict]:
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
