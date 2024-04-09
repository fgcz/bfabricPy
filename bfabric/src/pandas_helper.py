import pandas as pd
from typing import Any, List, Dict


def _stringify(a: Any) -> Any:
    """
    :param a: Any variable
    :return:  Stringified variable

    Convert variable to a string if it is of non-basic data type, otherwise keep it as it is
    TODO: Make a better separation between what is and what is not a basic data type
    """
    if isinstance(a, list) or isinstance(a, dict) or isinstance(a, tuple):
        return str(a)
    else:
        return a

def _stringify_dict(d: dict) -> dict:
    """
    :param d:  A dictionary
    :return:   Same dictionary, with all values stringified if necessary
    """
    return {k: _stringify(v) for k, v in d.items()}

def list_dict_to_df(l: List[Dict]) -> pd.DataFrame:
    """
    :param l: A list of dictionaries
    :return:  Pandas dataframe, where every list element is a new row

    * Columns are a union of all keys that appear in the dictionaries. Any missing key is treated as a NAN
    * All non-basic data types are converted to strings
    """
    return pd.DataFrame([_stringify_dict(r) for r in l])


if __name__ == "__main__":
    exampleLstDict = [
        {'cat': 1, 'dog': 2},
        {'cat': 3, 'mouse': ["a", "b"]},
        {'mouse': 5},
        {'cat': 1, 'dog': 2, 'mouse': 7},
    ]

    print(list_dict_to_df(exampleLstDict))
