from __future__ import annotations

from typing import Any, TYPE_CHECKING

from suds.sax.text import Text
from suds.sudsobject import asdict

if TYPE_CHECKING:
    Value = list["Value"] | dict[str, "Value"] | str | int | float | bool | None | Any


def convert_suds_type(item: Any) -> int | str | Any:
    """
    Converts the suds type to an equivalent python type. There is, to my knowledge, only a single suds type which
    is currently ever return, namely 'Text'. Integers and doubles are already cast to their python equivalents and
    thus do not need to be explicitly handled. This may be subject to change in future versions
    :param item: The suds item
    :return: The item as a built-in python type
    """
    if isinstance(item, Text):
        return str(item)
    return item


def suds_asdict_recursive(d: Any, convert_types: bool = False) -> dict[str, Value]:
    """Convert Suds object into serializable format.
    https://stackoverflow.com/a/15678861
    :param d: The input suds object
    :param convert_types: A boolean to determine if the simple types return should be cast to python types
    :return: The suds object converted to an OrderedDict
    """
    out: dict[str, Value] = {}
    for k, v in asdict(d).items():
        if hasattr(v, "__keylist__"):
            out[k] = suds_asdict_recursive(v, convert_types=convert_types)
        elif isinstance(v, list):
            items: list[Value] = []
            for item in v:
                if hasattr(item, "__keylist__"):
                    items.append(suds_asdict_recursive(item, convert_types=convert_types))
                else:
                    items.append(convert_suds_type(item) if convert_types else item)
            out[k] = items
        else:
            out[k] = convert_suds_type(v) if convert_types else v
    return out
