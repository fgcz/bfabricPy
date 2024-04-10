import io
import unittest

from bfabric.bfabric_config import BfabricConfig, BfabricAuth, parse_bfabricrc_py


class TestBfabricAuth(unittest.TestCase):
    def test_repr(self):
        auth = BfabricAuth("login", "password")
        rep = repr(auth)
        self.assertEqual("BfabricAuth(login='login', password=...)", rep)

    def test_str(self):
        auth = BfabricAuth("login", "password")
        rep = str(auth)
        self.assertEqual("BfabricAuth(login='login', password=...)", rep)


class TestBfabricConfig(unittest.TestCase):
    def setUp(self):
        self.config = BfabricConfig(
            base_url="url",
            application_ids={"app": 1},
        )

    def test_with_overrides(self):
        new_config = self.config.with_overrides(
            base_url="new_url",
            application_ids={"new": 2},
        )
        self.assertEqual("new_url", new_config.base_url)
        self.assertEqual({"new": 2}, new_config.application_ids)
        self.assertEqual("url", self.config.base_url)
        self.assertEqual({"app": 1}, self.config.application_ids)

    def test_with_replaced_when_none(self):
        new_config = self.config.with_overrides(base_url=None, application_ids=None)
        self.assertEqual("url", new_config.base_url)
        self.assertEqual({"app": 1}, new_config.application_ids)
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
            """_JOB_NOTIFICATION_EMAILS = "email1 email2"\n"""
        )
        file = io.StringIO(input_text)
        setattr(file, "name", "/file")
        with self.assertLogs(level="INFO") as log_context:
            config, auth = parse_bfabricrc_py(file)
        self.assertEqual("login", auth.login)
        self.assertEqual("user", auth.password)
        self.assertEqual("url", config.base_url)
        self.assertEqual({"app": 1}, config.application_ids)
        self.assertEqual("email1 email2", config.job_notification_emails)
        self.assertEqual(
            [
                "INFO:bfabric.bfabric_config:Reading configuration from: /file"
            ],
            log_context.output,
        )

    def test_read_bfabricrc_py_when_empty(self):
        input_text = ""
        file = io.StringIO(input_text)
        setattr(file, "name", "/file")
        with self.assertLogs(level="INFO"):
            config, auth = parse_bfabricrc_py(file)
        self.assertIsNone(auth)
        self.assertEqual("https://fgcz-bfabric.uzh.ch/bfabric", config.base_url)
        self.assertEqual({}, config.application_ids)
        self.assertEqual("", config.job_notification_emails)

    def test_repr(self):
        rep = repr(self.config)
        self.assertEqual(
            "BfabricConfig(base_url='url', application_ids={'app': 1}, job_notification_emails='')",
            rep,
        )

    def test_str(self):
        rep = str(self.config)
        self.assertEqual(
            "BfabricConfig(base_url='url', application_ids={'app': 1}, job_notification_emails='')",
            rep,
        )


if __name__ == "__main__":
    unittest.main()
