import os
import io
import unittest

from bfabric.bfabric_config import BfabricConfig, BfabricAuth, read_bfabricpy_yml


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
            webbase="url",
            application_ids={"app": 1},
        )

    def test_with_overrides(self):
        new_config = self.config.with_overrides(
            webbase="new_url",
            application_ids={"new": 2},
        )
        self.assertEqual("new_url", new_config.webbase)
        self.assertEqual({"new": 2}, new_config.application_ids)
        self.assertEqual("url", self.config.webbase)
        self.assertEqual({"app": 1}, self.config.application_ids)

    def test_with_replaced_when_none(self):
        new_config = self.config.with_overrides(webbase=None, application_ids=None)
        self.assertEqual("url", new_config.webbase)
        self.assertEqual({"app": 1}, new_config.application_ids)
        self.assertEqual("url", self.config.webbase)
        self.assertEqual({"app": 1}, self.config.application_ids)

    # Testing default initialization
    # TODO: Test that logging is consistent with initialization
    def test_read_yml_bypath_default(self):
        # Ensure environment variable is not available, and the default is environment is loaded
        os.environ.pop('BFABRICPY_CONFIG_ENV', None)

        config, auth = read_bfabricpy_yml('example_config.yml')  # Should deduce
        self.assertEqual("my_epic_production_login", auth.login)
        self.assertEqual("my_secret_production_password", auth.password)
        self.assertEqual("https://mega-production-server.uzh.ch/myprod", config.webbase)

    # Testing environment variable initialization
    # TODO: Test that logging is consistent with default config
    def test_read_yml_bypath_environment_variable(self):
        # Explicitly set the environment variable for this process
        os.environ["BFABRICPY_CONFIG_ENV"] = "TEST"

        config, auth = read_bfabricpy_yml('example_config.yml')  # Should deduce
        self.assertEqual("my_epic_test_login", auth.login)
        self.assertEqual("my_secret_test_password", auth.password)
        self.assertEqual("https://mega-test-server.uzh.ch/mytest", config.webbase)

    # Testing explicit initialization, as well as extra fields (application_ids, job_notification_emails)
    # TODO: Test that logging is consistent with default config
    def test_read_yml_bypath_allfields(self):
        with self.assertLogs(level="INFO") as log_context:
            config, auth = read_bfabricpy_yml('example_config.yml', config_env='TEST')

        # # Testing log
        # self.assertEqual(
        #     [
        #         "INFO:bfabric.bfabric_config:Reading configuration from: example_config.yml"
        #         "INFO:bfabric.bfabric_config:config environment specified explicitly as TEST"
        #     ],
        #     log_context.output,
        # )

        self.assertEqual("my_epic_test_login", auth.login)
        self.assertEqual("my_secret_test_password", auth.password)
        self.assertEqual("https://mega-test-server.uzh.ch/mytest", config.webbase)

        applications_dict_ground_truth = {
            'Proteomics/CAT_123': 7,
            'Proteomics/DOG_552': 6,
            'Proteomics/DUCK_666': 12
        }

        job_notification_emails_ground_truth = "john.snow@fgcz.uzh.ch billy.the.kid@fgcz.ethz.ch"

        self.assertEqual(applications_dict_ground_truth, config.application_ids)
        self.assertEqual(job_notification_emails_ground_truth, config.job_notification_emails)

    # Testing that we can load webbase without authentication if correctly requested
    def test_read_yml_when_empty_optional(self):
        with self.assertLogs(level="INFO"):
            config, auth = read_bfabricpy_yml('example_config.yml', config_env='STANDBY', optional_auth=True)

        self.assertIsNone(auth)
        self.assertEqual("https://standby-server.uzh.ch/mystandby", config.webbase)
        self.assertEqual({}, config.application_ids)
        self.assertEqual("", config.job_notification_emails)

    # Test that missing authentication will raise an error if required
    def test_read_yml_when_empty_mandatory(self):
        with self.assertRaises(ValueError):
            read_bfabricpy_yml('example_config.yml', config_env='STANDBY', optional_auth=False)

    def test_repr(self):
        rep = repr(self.config)
        self.assertEqual(
            "BfabricConfig(webbase='url', application_ids={'app': 1}, job_notification_emails='')",
            rep,
        )

    def test_str(self):
        rep = str(self.config)
        self.assertEqual(
            "BfabricConfig(webbase='url', application_ids={'app': 1}, job_notification_emails='')",
            rep,
        )


if __name__ == "__main__":
    unittest.main()
