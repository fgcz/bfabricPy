"""very experimental
"""

import requests
import unittest

from bfabric.bfabric2 import get_system_auth


class TestFlaskRESTProxy(unittest.TestCase):
    def setUp(self):
        self.rest_url = "http://localhost:5000"

        config, auth = get_system_auth(config_env="TEST")
        self.auth = auth

    def test_read(self):
        req_data = {"endpoint": "dataset", "query": {}, "login": self.auth.login, "webservicepassword": self.auth.password}
        print(requests.get(f"{self.rest_url}/read", json=req_data).json())
