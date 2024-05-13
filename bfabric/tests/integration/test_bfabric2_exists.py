import unittest
from bfabric.experimental.multi_query import  MultiQuery
from bfabric import BfabricAPIEngineType, Bfabric
from bfabric.bfabric import get_system_auth


class BfabricTestExists(unittest.TestCase):
    def setUp(self):
        self.config, self.auth = get_system_auth(config_env="TEST")

    def _test_single_exists(self, engine: BfabricAPIEngineType):
        bf = Bfabric(self.config, self.auth, engine=engine)
        multiquery = MultiQuery(bf)
        res = multiquery.exists("dataset", "id", 30721)  # Take ID which is the same as in production
        self.assertEqual(res, True)

    def test_zeep(self):
        self._test_single_exists(engine=BfabricAPIEngineType.ZEEP)

    def test_suds(self):
        self._test_single_exists(engine=BfabricAPIEngineType.SUDS)
