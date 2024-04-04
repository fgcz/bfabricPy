from collections import OrderedDict
from typing import Any, Union
from suds.sax.text import Text
from suds.sudsobject import asdict


def _recursive_asdict(d, convert_types: bool) -> OrderedDict:
    """Convert Suds object into serializable format.
    https://stackoverflow.com/a/15678861
    :param d: The input suds object
    :param convert_types: A boolean to determine if the simple types return should be cast to python types
    :return: The suds object converted to an OrderedDict
    """
    out = {}
    for k, v in asdict(d).items():
        if hasattr(v, '__keylist__'):
            out[k] = _recursive_asdict(v, convert_types)
        elif isinstance(v, list):
            out[k] = []
            for item in v:
                if hasattr(item, '__keylist__'):
                    out[k].append(_recursive_asdict(item, convert_types))
                else:
                    out[k].append(convert_suds_type(item) if convert_types else item)
        else:
            out[k] = convert_suds_type(v) if convert_types else v
    return OrderedDict(out)


def convert_suds_type(item: Any) -> Union[int, str]:
    """
    Converts the suds type to an equivalent python type. There is, to my knowledge, only a single suds type which
    is currently ever return, namely 'Text'. Integers and doubles are already cast to their python equivalents and
    thus do not need to be explicitly handled. This may be subject to change in future versions
    :param item: The suds item
    :return: The item as a built-in python type
    """
    if type(item) == Text:
        return str(item)
    return item


def suds_to_json(data, convert_types: bool = False):
    if type(data) == list:
        return [_recursive_asdict(d, convert_types) for d in data]
    return _recursive_asdict(data, convert_types)
