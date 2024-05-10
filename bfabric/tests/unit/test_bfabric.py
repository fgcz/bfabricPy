import datetime
import unittest
from functools import cached_property
from unittest.mock import MagicMock, patch, ANY

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

    @patch("bfabric.bfabric2.get_system_auth")
    def test_from_config_when_no_args(self, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config()
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        mock_get_system_auth.assert_called_once_with(config_env=None)

    @patch("bfabric.bfabric2.get_system_auth")
    def test_from_config_when_explicit_auth(self, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_config_auth = MagicMock(name="mock_config_auth")
        mock_get_system_auth.return_value = (mock_config, mock_config_auth)
        client = Bfabric.from_config(config_env="TestingEnv", auth=mock_auth)
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        mock_get_system_auth.assert_called_once_with(config_env="TestingEnv")

    @patch("bfabric.bfabric2.get_system_auth")
    def test_from_config_when_none_auth(self, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config(config_env="TestingEnv", auth=None)
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        with self.assertRaises(ValueError) as error:
            _ = client.auth
        self.assertIn("Authentication not available", str(error.exception))
        mock_get_system_auth.assert_called_once_with(config_env="TestingEnv")

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

    @patch.object(Bfabric, "save")
    def test_upload_resource(self, method_save):
        resource_name = "hello_world.txt"
        content = b"Hello, World!"
        workunit_id = 123
        check = MagicMock(name="check")
        self.mock_bfabric.upload_resource(resource_name, content, workunit_id, check)
        method_save.assert_called_once_with(
            endpoint="resource",
            obj={
                "base64": "SGVsbG8sIFdvcmxkIQ==",
                "workunitid": 123,
                "name": "hello_world.txt",
                "description": "base64 encoded file",
            },
            check=check,
        )

    def test_get_version_message(self):
        self.mock_config.base_url = "dummy_url"
        message = self.mock_bfabric.get_version_message()
        lines = message.split("\n")
        self.assertEqual(2, len(lines))
        # first line
        pattern = r"--- bfabricPy v\d+\.\d+\.\d+ \(EngineSUDS, dummy_url, U=None\) ---"
        self.assertRegex(lines[0], pattern)
        # second line
        year = datetime.datetime.now().year
        self.assertEqual(f"--- Copyright (C) 2014-{year} Functional Genomics Center Zurich ---", lines[1])

    @patch("bfabric.bfabric2.Console")
    @patch.object(Bfabric, "get_version_message")
    def test_print_version_message(self, method_get_version_message, mock_console):
        mock_stderr = MagicMock(name="mock_stderr")
        self.mock_bfabric.print_version_message(stderr=mock_stderr)
        mock_console.assert_called_once_with(stderr=mock_stderr, highlighter=ANY, theme=ANY)
        mock_console.return_value.print.assert_called_once_with(
            method_get_version_message.return_value, style="bright_yellow"
        )


if __name__ == "__main__":
    unittest.main()
