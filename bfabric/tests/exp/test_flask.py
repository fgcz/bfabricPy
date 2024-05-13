"""very experimental
"""

import datetime
import unittest

import requests

from bfabric.bfabric import get_system_auth


class TestFlaskRESTProxy(unittest.TestCase):
    def setUp(self):
        self.rest_url = "http://localhost:5000"

        config, auth = get_system_auth(config_env="TEST")
        self.auth = auth

        self.auth_dict = {"login": self.auth.login, "webservicepassword": self.auth.password}

    def test_read(self):
        req_data = {"endpoint": "dataset", "query": {}, **self.auth_dict}
        print(requests.post(f"{self.rest_url}/read", json=req_data).json())

    @unittest.skip
    def test_read_garbage_json(self):
        # TODO make it work
        garbage_json = "{aea"
        print(
            requests.post(
                f"{self.rest_url}/read", headers={"Content-Type": "application/json"}, data=garbage_json, verify=False
            ).json()
        )

    def test_save(self):
        now = datetime.datetime.now().isoformat()
        req_data = {"endpoint": "dataset", "query": {"id": 46178, "name": f"20240506 Testing {now}"}, **self.auth_dict}
        print(requests.post(f"{self.rest_url}/save", json=req_data).json())


if __name__ == "__main__":
    unittest.main()
