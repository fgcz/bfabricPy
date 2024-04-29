import unittest

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth


class BfabricTestExists(unittest.TestCase):
    def setUp(self):
        self.config, self.auth = get_system_auth(config_env="TEST")

    def _test_single_exists(self, engine: BfabricAPIEngineType):
        bf = Bfabric(self.config, self.auth, engine=engine)
        res = bf.exists('dataset', 'id', 30721)   # Take ID which is the same as in production
        self.assertEqual(res, True)

    def test_zeep(self):
        self._test_single_exists(engine=BfabricAPIEngineType.ZEEP)

    def test_suds(self):
        self._test_single_exists(engine=BfabricAPIEngineType.SUDS)
