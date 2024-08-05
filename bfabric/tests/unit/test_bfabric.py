import datetime
import unittest
from functools import cached_property
from unittest.mock import MagicMock, patch, ANY, call

from bfabric import Bfabric, BfabricAPIEngineType
from bfabric.engine.engine_suds import EngineSUDS


class TestBfabric(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock(name="mock_config", spec=["base_url"])
        self.mock_auth = None
        self.mock_engine_type = BfabricAPIEngineType.SUDS
        self.mock_engine = MagicMock(name="mock_engine", spec=EngineSUDS)

    @cached_property
    def mock_bfabric(self) -> Bfabric:
        return Bfabric(config=self.mock_config, auth=self.mock_auth, engine=self.mock_engine_type)

    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineSUDS")
    def test_from_config_when_no_args(self, _mock_engine_suds, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config()
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)

    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineSUDS")
    def test_from_config_when_explicit_auth(self, _mock_engine_suds, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_config_auth = MagicMock(name="mock_config_auth")
        mock_get_system_auth.return_value = (mock_config, mock_config_auth)
        client = Bfabric.from_config(config_env="TestingEnv", auth=mock_auth)
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        mock_get_system_auth.assert_called_once_with(config_env="TestingEnv", config_path=None)

    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineSUDS")
    def test_from_config_when_none_auth(self, _mock_engine_suds, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config(config_env="TestingEnv", auth=None)
        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        with self.assertRaises(ValueError) as error:
            _ = client.auth
        self.assertIn("Authentication not available", str(error.exception))
        mock_get_system_auth.assert_called_once_with(config_env="TestingEnv", config_path=None)

    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineSUDS")
    def test_from_config_when_engine_suds(self, mock_engine_suds, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config(engine=BfabricAPIEngineType.SUDS)

        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        self.assertEqual(mock_engine_suds.return_value, client.engine)
        mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)

        mock_engine_suds.assert_called_once_with(base_url=mock_config.base_url)
        self.assertEqual(mock_engine_suds.return_value, client.engine)

    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineZeep")
    def test_from_config_when_engine_zeep(self, mock_engine_zeep, mock_get_system_auth):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config(engine=BfabricAPIEngineType.ZEEP)

        self.assertIsInstance(client, Bfabric)
        self.assertEqual(mock_config, client.config)
        self.assertEqual(mock_auth, client.auth)
        self.assertEqual(mock_engine_zeep.return_value, client.engine)
        mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)

        mock_engine_zeep.assert_called_once_with(base_url=mock_config.base_url)
        self.assertEqual(mock_engine_zeep.return_value, client.engine)

    @patch.object(Bfabric, "print_version_message")
    @patch("bfabric.bfabric.get_system_auth")
    @patch("bfabric.bfabric.EngineSUDS")
    def test_from_config_when_verbose(self, _mock_engine_suds, mock_get_system_auth, mock_print_version_message):
        mock_config = MagicMock(name="mock_config")
        mock_auth = MagicMock(name="mock_auth")
        mock_get_system_auth.return_value = (mock_config, mock_auth)
        client = Bfabric.from_config(verbose=True)
        mock_print_version_message.assert_called_once_with()

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

    def test_read_when_no_pages_available_and_check(self):
        self.mock_auth = MagicMock(name="mock_auth")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_result = MagicMock(name="mock_result", total_pages_api=0, assert_success=MagicMock())
            mock_engine.read.return_value = mock_result
            result = self.mock_bfabric.read(endpoint="mock_endpoint", obj="mock_obj")
            self.assertEqual(mock_result.get_first_n_results.return_value, result)
            mock_engine.read.assert_called_once_with(
                endpoint="mock_endpoint", obj="mock_obj", auth=self.mock_auth, page=1, return_id_only=False
            )
            mock_result.assert_success.assert_called_once_with()
            mock_result.get_first_n_results.assert_called_once_with(100)

    @patch("bfabric.bfabric.compute_requested_pages")
    def test_read_when_pages_available_and_check(self, mock_compute_requested_pages):
        self.mock_auth = MagicMock(name="mock_auth")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_page_results = [
                MagicMock(
                    name="mock_page_result_1",
                    assert_success=MagicMock(),
                    total_pages_api=3,
                    errors=[],
                ),
                MagicMock(
                    name="mock_page_result_2",
                    assert_success=MagicMock(),
                    total_pages_api=3,
                    errors=[],
                ),
                MagicMock(
                    name="mock_page_result_3",
                    assert_success=MagicMock(),
                    total_pages_api=3,
                    errors=[],
                ),
            ]
            mock_page_results[0].__getitem__.side_effect = lambda i: [1, 2, 3, 4, 5][i]
            mock_page_results[1].__getitem__.side_effect = lambda i: [6, 7, 8, 9, 10][i]
            mock_page_results[2].__getitem__.side_effect = lambda i: [11, 12, 13, 14, 15][i]

            mock_engine.read.side_effect = lambda **kwargs: mock_page_results[kwargs["page"] - 1]
            mock_compute_requested_pages.return_value = ([1, 2], 4)

            result = self.mock_bfabric.read(endpoint="mock_endpoint", obj="mock_obj")

            mock_compute_requested_pages.assert_called_once_with(
                n_page_total=3,
                n_item_per_page=100,
                n_item_offset=0,
                n_item_return_max=100,
            )
            self.assertListEqual([], result.errors)
            self.assertListEqual(
                [
                    call.read(
                        endpoint="mock_endpoint", obj="mock_obj", auth=self.mock_auth, page=1, return_id_only=False
                    ),
                    call.read(
                        endpoint="mock_endpoint", obj="mock_obj", auth=self.mock_auth, page=2, return_id_only=False
                    ),
                ],
                mock_engine.mock_calls,
            )
            self.assertEqual(6, len(result))
            self.assertEqual(5, result[0])
            self.assertEqual(10, result[5])

    def test_save_when_no_auth(self):
        endpoint = "test_endpoint"
        obj = {"key": "value"}
        with patch.object(self.mock_bfabric, "engine") as mock_engine, self.assertRaises(ValueError) as error:
            self.mock_bfabric.save(endpoint, obj)
        self.assertEqual("Authentication not available", str(error.exception))
        mock_engine.save.assert_not_called()

    def test_save_when_auth_and_check_false(self):
        endpoint = "test_endpoint"
        obj = {"key": "value"}
        self.mock_auth = MagicMock(name="mock_auth")
        method_assert_success = MagicMock(name="method_assert_success")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_engine.save.return_value.assert_success = method_assert_success
            result = self.mock_bfabric.save(endpoint, obj, check=False)
        self.assertEqual(mock_engine.save.return_value, result)
        method_assert_success.assert_not_called()
        mock_engine.save.assert_called_once_with(endpoint=endpoint, obj=obj, auth=self.mock_auth)

    def test_save_when_auth_and_check_true(self):
        endpoint = "test_endpoint"
        obj = {"key": "value"}
        self.mock_auth = MagicMock(name="mock_auth")
        method_assert_success = MagicMock(name="method_assert_success")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_engine.save.return_value.assert_success = method_assert_success
            result = self.mock_bfabric.save(endpoint, obj)
        self.assertEqual(mock_engine.save.return_value, result)
        method_assert_success.assert_called_once_with()
        mock_engine.save.assert_called_once_with(endpoint=endpoint, obj=obj, auth=self.mock_auth)

    def test_delete_when_no_auth(self):
        endpoint = "test_endpoint"
        obj = {"key": "value"}
        with patch.object(self.mock_bfabric, "engine") as mock_engine, self.assertRaises(ValueError) as error:
            self.mock_bfabric.delete(endpoint, obj)
        self.assertEqual("Authentication not available", str(error.exception))
        mock_engine.delete.assert_not_called()

    def test_delete_when_auth_and_check_false(self):
        endpoint = "test_endpoint"
        self.mock_auth = MagicMock(name="mock_auth")
        method_assert_success = MagicMock(name="method_assert_success")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_engine.delete.return_value.assert_success = method_assert_success
            result = self.mock_bfabric.delete(endpoint=endpoint, id=10, check=False)
        self.assertEqual(mock_engine.delete.return_value, result)
        method_assert_success.assert_not_called()
        mock_engine.delete.assert_called_once_with(endpoint=endpoint, id=10, auth=self.mock_auth)

    def test_delete_when_auth_and_check_true(self):
        endpoint = "test_endpoint"
        self.mock_auth = MagicMock(name="mock_auth")
        method_assert_success = MagicMock(name="method_assert_success")
        with patch.object(self.mock_bfabric, "engine") as mock_engine:
            mock_engine.delete.return_value.assert_success = method_assert_success
            result = self.mock_bfabric.delete(endpoint=endpoint, id=10)
        self.assertEqual(mock_engine.delete.return_value, result)
        method_assert_success.assert_called_once_with()
        mock_engine.delete.assert_called_once_with(endpoint=endpoint, id=10, auth=self.mock_auth)

    @patch.object(Bfabric, "read")
    def test_exists_when_true(self, method_read):
        method_read.return_value.__len__.return_value = 1
        self.assertTrue(self.mock_bfabric.exists(endpoint="test_endpoint", key="key", value="value"))
        method_read.assert_called_once_with(
            endpoint="test_endpoint", obj={"key": "value"}, max_results=1, check=True, return_id_only=True
        )

    @patch.object(Bfabric, "read")
    def test_exists_when_true_and_extra_args(self, method_read):
        method_read.return_value.__len__.return_value = 1
        self.assertTrue(
            self.mock_bfabric.exists(
                endpoint="test_endpoint", key="key", value="value", query={"extra": "arg"}, check=False
            )
        )
        method_read.assert_called_once_with(
            endpoint="test_endpoint",
            obj={"key": "value", "extra": "arg"},
            max_results=1,
            check=False,
            return_id_only=True,
        )

    @patch.object(Bfabric, "read")
    def test_exists_when_false(self, method_read):
        method_read.return_value.__len__.return_value = 0
        self.assertFalse(self.mock_bfabric.exists(endpoint="test_endpoint", key="key", value="value"))
        method_read.assert_called_once_with(
            endpoint="test_endpoint", obj={"key": "value"}, max_results=1, check=True, return_id_only=True
        )

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
        message = self.mock_bfabric._get_version_message()
        lines = message.split("\n")
        self.assertEqual(2, len(lines))
        # first line
        pattern = r"--- bfabricPy v\d+\.\d+\.\d+ \(EngineSUDS, dummy_url, U=None\) ---"
        self.assertRegex(lines[0], pattern)
        # second line
        year = datetime.datetime.now().year
        self.assertEqual(f"--- Copyright (C) 2014-{year} Functional Genomics Center Zurich ---", lines[1])

    @patch("bfabric.bfabric.Console")
    @patch.object(Bfabric, "get_version_message")
    def test_print_version_message(self, method_get_version_message, mock_console):
        mock_stderr = MagicMock(name="mock_stderr")
        self.mock_bfabric._log_version_message(stderr=mock_stderr)
        mock_console.assert_called_once_with(stderr=mock_stderr, highlighter=ANY, theme=ANY)
        mock_console.return_value.print.assert_called_once_with(
            method_get_version_message.return_value, style="bright_yellow"
        )


if __name__ == "__main__":
    unittest.main()
