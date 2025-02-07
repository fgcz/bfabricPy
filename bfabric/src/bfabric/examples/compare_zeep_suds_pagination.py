import os

import pandas as pd

from bfabric import Bfabric, BfabricAPIEngineType
from bfabric.bfabric import get_system_auth
from bfabric.results.pandas_helper import list_dict_to_df

"""
This will eventually become a test that will compare Zeep and Suds paginated output
Strategy:
1. Make a query for 300 entries from user for both Zeep and Suds
2. Concatenate all entries into a dataframe, transforming all hierarchical non-basic types to a string
3. For all practical purposes, the resulting dataframes should be the same

Observations:
* There are mismatches in the fields of "project" and "formerproject", where about half of projects are not
   correctly parsed by Zeep.
"""


def report_test_result(rez: bool, prefix: str) -> None:
    if rez:
        print("--", prefix, "test passed --")
    else:
        print("--", prefix, "test failed --")


def _calc_query(config, auth, engine, endpoint):
    print("Sending query via", engine)
    b = Bfabric(config, auth, engine=engine)

    response_class = b.read(
        endpoint,
        {},
        max_results=300,
        return_id_only=False,
        includedeletableupdateable=True,
    )
    response_dict = response_class.to_list_dict(drop_empty=True, have_sort_responses=True)
    return list_dict_to_df(response_dict)


def _set_partition_test(a, b) -> bool:
    aSet = set(a)
    bSet = set(b)
    shared = aSet.intersection(bSet)
    unique1 = aSet - bSet
    unique2 = bSet - aSet

    print("Shared:", shared)
    print("Unique(1):", unique1)
    print("Unique(2):", unique2)

    # Test passes if there are no entities unique to only one of the sets
    return (len(unique1) == 0) and (len(unique2) == 0)


def dataframe_pagination_test(config, auth, endpoint, use_cached: bool = False, store_cached: bool = True):
    pwd_zeep = "tmp_zeep_" + endpoint + ".csv"
    pwd_suds = "tmp_suds_" + endpoint + ".csv"

    if use_cached and os.path.isfile(pwd_zeep) and os.path.isfile(pwd_suds):
        print("Reading cached dataframes for", endpoint)
        resp_df_suds = pd.read_csv(pwd_zeep)
        resp_df_zeep = pd.read_csv(pwd_suds)
    else:
        print("Running queries from scratch for", endpoint)
        resp_df_suds = _calc_query(config, auth, BfabricAPIEngineType.SUDS, endpoint)
        resp_df_zeep = _calc_query(config, auth, BfabricAPIEngineType.ZEEP, endpoint)
        if store_cached:
            resp_df_suds.to_csv(pwd_zeep)
            resp_df_zeep.to_csv(pwd_suds)

    # Rename suds to remove underscores
    resp_df_suds.rename(columns={"_id": "id", "_classname": "classname"}, inplace=True)

    suds_cols = list(sorted(resp_df_suds.columns))
    zeep_cols = list(sorted(resp_df_zeep.columns))

    # Report
    set_test_result = _set_partition_test(suds_cols, zeep_cols)
    report_test_result(set_test_result, "set")
    if not set_test_result:
        return False

    match_test_result = True
    for col_name in suds_cols:
        if not resp_df_suds[col_name].equals(resp_df_zeep[col_name]):
            print("------- Mismatch in: ", col_name, "-------")
            print("Suds", list(resp_df_suds[col_name]))
            print("Zeep", list(resp_df_zeep[col_name]))
            match_test_result = False

    return match_test_result


config, auth = get_system_auth(config_env="TEST")

result = dataframe_pagination_test(config, auth, "user", use_cached=False, store_cached=True)
report_test_result(result, "pagination")
