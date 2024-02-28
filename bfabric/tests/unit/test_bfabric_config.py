import io
import unittest

from bfabric.bfabric_config import BfabricConfig


class TestBfabricConfig(unittest.TestCase):
    def setUp(self):
        self.config = BfabricConfig(
            login="login",
            password="user",
            base_url="url",
            application_ids={"app": 1},
        )

    def test_with_overrides(self):
        new_config = self.config.with_overrides(
            login="new_login",
            password="new_user",
            base_url="new_url",
            application_ids={"new": 2},
        )
        self.assertEqual("new_login", new_config.login)
        self.assertEqual("new_user", new_config.password)
        self.assertEqual("new_url", new_config.base_url)
        self.assertEqual({"new": 2}, new_config.application_ids)
        self.assertEqual("login", self.config.login)
        self.assertEqual("user", self.config.password)
        self.assertEqual("url", self.config.base_url)
        self.assertEqual({"app": 1}, self.config.application_ids)

    def test_with_replaced_when_none(self):
        new_config = self.config.with_overrides(
            login=None, password=None, base_url=None, application_ids=None
        )
        self.assertEqual("login", new_config.login)
        self.assertEqual("user", new_config.password)
        self.assertEqual("url", new_config.base_url)
        self.assertEqual({"app": 1}, new_config.application_ids)
        self.assertEqual("login", self.config.login)
        self.assertEqual("user", self.config.password)
        self.assertEqual("url", self.config.base_url)
        self.assertEqual({"app": 1}, self.config.application_ids)

    def test_read_bfabricrc_py(self):
        input_text = (
            "# Some comment\n"
            "_LOGIN = login\n"
            "_PASSWD = 'user'\n"
            "_UKNOWNKEY = 'value'\n"
            "# Another comment\n"
            """_WEBBASE = "url"\n"""
            """_APPLICATION = {"app": 1}\n"""
        )
        file = io.StringIO(input_text)
        setattr(file, "name", "/file")
        with self.assertLogs(level="INFO") as log_context:
            config = BfabricConfig.read_bfabricrc_py(file)
        self.assertEqual("login", config.login)
        self.assertEqual("user", config.password)
        self.assertEqual("url", config.base_url)
        self.assertEqual({"app": 1}, config.application_ids)
        self.assertEqual(
            [
                "INFO:bfabric.bfabric_config.BfabricConfig:Reading configuration from: /file"
            ],
            log_context.output,
        )

    def test_read_bfabricrc_py_when_empty(self):
        input_text = ""
        file = io.StringIO(input_text)
        setattr(file, "name", "/file")
        with self.assertLogs(level="INFO"):
            config = BfabricConfig.read_bfabricrc_py(file)
        self.assertIsNone(config.login)
        self.assertIsNone(config.password)
        self.assertEqual("https://fgcz-bfabric.uzh.ch/bfabric", config.base_url)
        self.assertEqual({}, config.application_ids)

    def test_repr(self):
        rep = repr(self.config)
        self.assertEqual(
            "BfabricConfig(login='login', password=..., base_url='url', application_ids={'app': 1})",
            rep,
        )


if __name__ == "__main__":
    unittest.main()
