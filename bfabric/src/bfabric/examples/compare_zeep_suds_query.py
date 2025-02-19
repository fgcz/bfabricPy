from collections import OrderedDict
from contextlib import redirect_stdout
from copy import deepcopy

import suds
import zeep

from bfabric import BfabricAuth, BfabricClientConfig
from bfabric.bfabric import get_system_auth
from bfabric.results.response_format_dict import drop_empty_elements, map_element_keys
from bfabric.engine.response_format_suds import suds_asdict_recursive

"""
This file is intended to eventually become a test to compare that Zeep and SUDS produce
the same or at least comparable output for the same requests. Important features
* Test if raw XML matches
* Test if parsed response (asdict) matches
For both, it is important to test
* different endpoints (user, run, ...)
* single match queries (e.g. {id=5}) vs multi match queries (e.g. {})

Observations:
* SUDS produces underscores in front of 'id', 'projectid' and 'classname'. Reasons currently unknown, may also affect
    other keywords. Currently, we remove underscores by explicitly providing keywords which to purge
* ZEEP does not match XML
    - Zeep generates additional keywords not present in XML, all of them have values None or empty list
    - Zeep misses some important keywords like 'id' and 'projectid' inside of nested XML, such as user->project. This
        behaviour is inconsistent, and only affects a fraction of users.
"""


def read_zeep(wsdl, fullQuery, raw=True):
    client = zeep.Client(wsdl)
    with client.settings(strict=False, raw_response=raw):
        ret = client.service.read(fullQuery)
    if raw:
        return ret.content
    else:
        return dict(zeep.helpers.serialize_object(ret, target_cls=dict))


def read_suds(wsdl, fullQuery, raw=True):
    client = suds.client.Client(wsdl, cache=None, retxml=raw)
    ret = client.service.read(fullQuery)
    if raw:
        return ret
    else:
        return suds_asdict_recursive(ret, convert_types=True)


def full_query(auth: BfabricAuth, query: dict, includedeletableupdateable: bool = False) -> dict:
    thisQuery = deepcopy(query)
    thisQuery["includedeletableupdateable"] = includedeletableupdateable

    return {"login": auth.login, "password": auth.password.get_secret_value(), "query": thisQuery}


def calc_both(
    auth: BfabricAuth,
    config: BfabricClientConfig,
    endpoint: str,
    query: dict,
    raw: bool = True,
):
    wsdl = "".join((config.base_url, "/", endpoint, "?wsdl"))
    fullQuery = full_query(auth, query)
    retZeep = read_zeep(wsdl, fullQuery, raw=raw)
    retSuds = read_suds(wsdl, fullQuery, raw=raw)
    return retZeep, retSuds


######################
# Raw XML tests
######################


def raw_test(auth: BfabricAuth, config: BfabricClientConfig, endpoint, query) -> None:
    print("Testing raw XML match for", endpoint, query)
    retZeep, retSuds = calc_both(auth, config, endpoint, query, raw=True)
    assert len(retZeep) == len(retSuds)
    assert retZeep == retSuds
    print("-- passed --")


config, auth = get_system_auth(config_env="TEST")
# raw_test(auth, config, 'user', {'id': 9026})
# raw_test(auth, config, 'user', {})

# root = etree.fromstring(retZeep)
# print(etree.tostring(root, pretty_print=True).decode())
# pprint(retZeepDict['user'][0]['order'])


######################
# Parsed dict comparison
######################


# Find the set of all basic types used in the nested container (made of dicts, ordered dicts and lists)
def recursive_get_types(generic_container) -> set:
    if isinstance(generic_container, (dict, OrderedDict)):
        type_sets_lst = [recursive_get_types(v) for k, v in generic_container.items()]
        return set().union(*type_sets_lst)
    elif isinstance(generic_container, list):
        type_sets_lst = [recursive_get_types(el) for el in generic_container]
        return set().union(*type_sets_lst)
    else:
        return {type(generic_container)}


def basic_data_type_match_test(auth, config, endpoint, query) -> None:
    print("Testing data types for", endpoint, query)
    retZeepDict, retSudsDict = calc_both(auth, config, endpoint, query, raw=False)
    typesZeep = recursive_get_types(retZeepDict)
    typesSuds = recursive_get_types(retZeepDict)
    print("Zeep", typesZeep)
    print("Suds", typesSuds)


# basic_data_type_match_test(auth, config, 'user', {'id': 9026})
# basic_data_type_match_test(auth, config, 'user', {})


# Compare two dictionaries/lists recursively. Print every time there is a discrepancy
def recursive_comparison(generic_container1, generic_container2, prefix: list) -> bool:
    matched = True

    if type(generic_container1) != type(generic_container2):
        print(prefix, "type", type(generic_container1), "!=", type(generic_container2))
        return False
    if isinstance(generic_container1, dict):
        allKeys = set(list(generic_container1.keys()) + list(generic_container2.keys()))
        for k in allKeys:
            if k not in generic_container1:
                print(prefix, "Not in 1: ", k, "=", generic_container2[k])
                print("- 1:", generic_container1)
                print("- 2:", generic_container2)
                matched = False
            elif k not in generic_container2:
                print(prefix, "Not in 2: ", k, "=", generic_container1[k])
                matched = False
            else:
                matched_recursive = recursive_comparison(generic_container1[k], generic_container2[k], prefix + [k])
                matched = matched and matched_recursive
    elif isinstance(generic_container1, list):
        if len(generic_container1) != len(generic_container2):
            print(prefix, "length", len(generic_container1), "!=", len(generic_container2))
            matched = False
        else:
            for i, (el1, el2) in enumerate(zip(generic_container1, generic_container2)):
                matched_recursive = recursive_comparison(el1, el2, prefix + [i])
                matched = matched and matched_recursive
    else:
        if generic_container1 != generic_container2:
            print(prefix, "value", generic_container1, "!=", generic_container2)
            matched = False

    return matched


def parsed_data_match_test(
    auth,
    config,
    endpoint,
    query,
    drop_empty: bool = True,
    drop_underscores_suds: bool = True,
    log_file_path: str = None,
) -> None:
    print("Testing parsed data match for", endpoint, query)
    retZeepDict, retSudsDict = calc_both(auth, config, endpoint, query, raw=False)

    if drop_empty:
        drop_empty_elements(retZeepDict, inplace=True)
        drop_empty_elements(retSudsDict, inplace=True)

    if drop_underscores_suds:
        map_element_keys(
            retSudsDict,
            {"_id": "id", "_classname": "classname", "_projectid": "projectid"},
            inplace=True,
        )

    if log_file_path is not None:
        with open(log_file_path, "w") as f, redirect_stdout(f):
            matched = recursive_comparison(retZeepDict, retSudsDict, prefix=[])
    else:
        matched = recursive_comparison(retZeepDict, retSudsDict, prefix=[])

    if matched:
        print("-- passed --")
    else:
        print("-- failed --")


parsed_data_match_test(
    auth,
    config,
    "user",
    {"id": 9026},
    drop_empty=True,
    drop_underscores_suds=True,
    log_file_path=None,
)
#
# parsed_data_match_test(auth, config, 'user', {}, drop_empty=True, drop_underscores_suds=True,
#                        log_file_path=None)

# parsed_data_match_test(auth, config, 'run', {}, drop_empty=True, drop_underscores_suds=True,
#                        log_file_path=None)

# print("Zeep", retZeep['user'][0]['project'][0])
# print("Suds", retSuds['user'][0]['project'][0])

# print("Zeep", retZeep['user'][0])
# print("Suds", retSuds['user'][0])
