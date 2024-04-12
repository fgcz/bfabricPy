import sys
from collections import OrderedDict
from lxml import etree
from pprint import pprint

import zeep
import suds

from bfabric.bfabric2 import get_system_auth
from bfabric.src.suds_format import suds_asdict_recursive
from bfabric.src.iter_helper import drop_empty_response_elements, map_response_element_keys


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


config, auth = get_system_auth()

endpoint = 'user'
wsdl = "".join((config.base_url, '/', endpoint, "?wsdl"))

fullQuery = {
    'login': auth.login,
    'password': auth.password,
    'query': {'includedeletableupdateable': False}
    # 'query': {'id': 9026, 'includedeletableupdateable': False}
}

######################
# Raw XML comparison
######################

# retZeepDict = read_zeep(wsdl, fullQuery, raw=False)
# retSudsDict = read_suds(wsdl, fullQuery, raw=False)
# retZeep = read_zeep(wsdl, fullQuery, raw=True)
# retSuds = read_suds(wsdl, fullQuery, raw=True)
# print(retZeep)
# print(retSuds)

# print(len(retZeep))
# print(len(retSuds))
# print(retZeep == retSuds)

# print(retZeep)
# print('coachedorder' in str(retZeep))

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


# Compare two dictionaries/lists recursively. Print every time there is a discrepancy
def recursive_comparison(generic_container1, generic_container2, prefix: list):
    if type(generic_container1) != type(generic_container2):
        print(prefix, "type", type(generic_container1), "!=", type(generic_container2))
        return
    if isinstance(generic_container1, dict):
        allKeys = set(list(generic_container1.keys()) + list(generic_container2.keys()))
        for k in allKeys:
            if k not in generic_container1:
                print(prefix, "Not in 1: ", k, '=', generic_container2[k])
                print("- 1:", generic_container1)
                print("- 2:", generic_container2)
            elif k not in generic_container2:
                print(prefix, "Not in 2: ", k, '=', generic_container1[k])
            else:
                recursive_comparison(generic_container1[k], generic_container2[k], prefix + [k])
    elif isinstance(generic_container1, list):
        if len(generic_container1) != len(generic_container2):
            print(prefix, "length", len(generic_container1), '!=', len(generic_container2))
        else:
            for i, (el1, el2) in enumerate(zip(generic_container1, generic_container2)):
                recursive_comparison(el1, el2, prefix + [i])
    else:
        if generic_container1 != generic_container2:
            print(prefix, "value", generic_container1, "!=", generic_container2)

retZeep = read_zeep(wsdl, fullQuery, raw=False)
retSuds = read_suds(wsdl, fullQuery, raw=False)

# print("Zeep", retZeep['user'][0]['project'][0])
# print("Suds", retSuds['user'][0]['project'][0])

# print("Zeep", retZeep['user'][0])
# print("Suds", retSuds['user'][0])


drop_empty_response_elements(retZeep, inplace=True)
drop_empty_response_elements(retSuds, inplace=True)
map_response_element_keys(retSuds, {'_id': 'id', '_classname': 'classname', '_projectid': 'projectid'}, inplace=True)


# print(len(retZeep))
# print(retZeep)
# print(retSuds)

# print(recursive_get_types(retZeep))

from contextlib import redirect_stdout

# with open('compare_result.txt', 'w') as f:
#     with redirect_stdout(f):
#         recursive_comparison(retZeep, retSuds, prefix = [])
recursive_comparison(retZeep, retSuds, prefix = [])

# print(retSuds)