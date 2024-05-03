import unittest
from functools import cached_property
from unittest.mock import MagicMock

from bfabric import BfabricConfig
from bfabric.bfabric2 import BfabricAPIEngineType, Bfabric
from bfabric.src.engine_suds import EngineSUDS


class TestBfabric(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock(name="mock_config", spec=BfabricConfig)
        self.mock_auth = None
        self.mock_engine_type = BfabricAPIEngineType.SUDS
        self.mock_engine = MagicMock(name="mock_engine", spec=EngineSUDS)

    @cached_property
    def mock_bfabric(self) -> Bfabric:
        return Bfabric(config=self.mock_config, auth=self.mock_auth, engine=self.mock_engine_type)

    def test_query_counter(self):
        self.assertEqual(0, self.mock_bfabric.query_counter)

    def test_config(self):
        self.assertEqual(self.mock_config, self.mock_bfabric.config)

    def test_auth_when_missing(self):
        with self.assertRaises(ValueError) as error:
            _ = self.mock_bfabric.auth
        self.assertIn("Authentication not available", str(error.exception))

    def test_auth_when_provided(self):
        self.mock_auth = MagicMock(name="mock_auth")
        self.assertEqual(self.mock_auth, self.mock_bfabric.auth)

    def test_with_auth(self):
        mock_old_auth = MagicMock(name="mock_old_auth")
        mock_new_auth = MagicMock(name="mock_new_auth")
        self.mock_auth = mock_old_auth
        with self.mock_bfabric.with_auth(mock_new_auth):
            self.assertEqual(mock_new_auth, self.mock_bfabric.auth)
        self.assertEqual(mock_old_auth, self.mock_bfabric.auth)

    def test_with_auth_when_exception(self):
        mock_old_auth = MagicMock(name="mock_old_auth")
        mock_new_auth = MagicMock(name="mock_new_auth")
        self.mock_auth = mock_old_auth
        try:
            with self.mock_bfabric.with_auth(mock_new_auth):
                raise ValueError("Test exception")
        except ValueError:
            pass
        self.assertEqual(mock_old_auth, self.mock_bfabric.auth)

    # TODO further unit tests


if __name__ == "__main__":
    unittest.main()
