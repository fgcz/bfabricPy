import unittest

from bfabric import BfabricAPIEngineType, Bfabric


class BfabricTestExists(unittest.TestCase):
    def _test_single_exists(self, engine: BfabricAPIEngineType):
        client = Bfabric.from_config("TEST", engine=engine)
        res = client.exists("dataset", "id", 30721)
        self.assertEqual(res, True)

    def test_zeep(self):
        self._test_single_exists(engine=BfabricAPIEngineType.ZEEP)

    def test_suds(self):
        self._test_single_exists(engine=BfabricAPIEngineType.SUDS)


if __name__ == "__main__":
    pass
