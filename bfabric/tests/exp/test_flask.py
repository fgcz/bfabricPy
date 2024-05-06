"""very experimental
"""

import unittest

import requests

from bfabric.bfabric2 import get_system_auth


class TestFlaskRESTProxy(unittest.TestCase):
    def setUp(self):
        self.rest_url = "http://localhost:5000"

        config, auth = get_system_auth(config_env="TEST")
        self.auth = auth

    def test_read(self):
        req_data = {"endpoint": "dataset", "query": {}, "login": self.auth.login, "webservicepassword": self.auth.password}
        print(requests.post(f"{self.rest_url}/read", json=req_data).json())

    @unittest.skip
    def test_read_garbage_json(self):
        # TODO make it work
        garbage_json = "{aea"
        print(requests.post(
            f"{self.rest_url}/read",
            headers={"Content-Type": "application/json"},
            data=garbage_json,
            verify=False
        ).json())




if __name__ == "__main__":
    unittest.main()
