import unittest
import pandas as pd

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth
from bfabric.src.pandas_helper import list_dict_to_df


def _calc_query(config, auth, engine: BfabricAPIEngineType, endpoint: str,
                max_results: int = 300) -> pd.DataFrame:
    print("Sending query via", engine)
    b = Bfabric(config, auth, engine=engine)

    response_class = b.read(endpoint, {}, max_results=max_results, idonly=False, includedeletableupdateable=True)
    response_dict = response_class.to_list_dict(drop_empty=True, drop_underscores_suds=True,
                                                have_sort_responses=True)
    return list_dict_to_df(response_dict)


class BfabricTestPagination(unittest.TestCase):
    def setUp(self):
        self.config, self.auth = get_system_auth()

    def test_composite_user(self):
        endpoint = 'user'
        max_results = 300

        # Test SUDS
        print("Testing if SUDS returns the requested number of entries")
        resp_df_suds = _calc_query(self.config, self.auth, BfabricAPIEngineType.SUDS, endpoint,
                                   max_results=max_results)
        assert len(resp_df_suds.index) == max_results

        # Test ZEEP
        print("Testing if ZEEP returns the requested number of entries")
        resp_df_zeep = _calc_query(self.config, self.auth, BfabricAPIEngineType.ZEEP, endpoint,
                                   max_results=max_results)
        assert len(resp_df_zeep.index) == max_results

        # Rename suds to remove underscores
        # resp_df_suds.rename(columns={"_id": "id", "_classname": "classname"}, inplace=True)

        # Test that columns are exactly the same
        print("Testing if SUDS and ZEEP parsed responses have the same root fields")
        suds_cols = sorted(resp_df_suds.columns)
        zeep_cols = sorted(resp_df_zeep.columns)
        assert suds_cols == zeep_cols

        print("Testing if SUDS and ZEEP responses are the same field by field")
        mismatch_cols = []
        for col_name in suds_cols:
            if not resp_df_suds[col_name].equals(resp_df_zeep[col_name]):
                mismatch_cols += [col_name]

        # TODO: Make the test strict if Zeep bug is ever resolved.
        assert mismatch_cols == ['formerproject', 'project']
        print("SUDS and ZEEP mismatch in", mismatch_cols, "(expected)")
