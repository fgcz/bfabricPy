import datetime
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bfabric.bfabric2 import Bfabric
from bfabric.tests.integration.integration_test_helper import DeleteEntities


class TestUploadResource(unittest.TestCase):
    def setUp(self):
        self.client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.delete_results = DeleteEntities(client=self.client, created_entities=[])
        self.addCleanup(self.delete_results)
        self.container_id = 3000

    def test_upload_resource(self):
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            file = work_dir / "test.txt"
            file.write_text("Hello World!")

            ts = datetime.datetime.now().isoformat()
            # create workunit
            workunit = self.client.save(
                "workunit", {"containerid": self.container_id, "name": f"Testing {ts}", "applicationid": 1}
            ).to_list_dict()[0]
            self.delete_results.created_entities.append(("workunit", workunit["id"]))

            # upload resource
            resp = self.client.upload_resource(
                resource_name=file.name, content=file.read_bytes(), workunit_id=workunit["id"]
            ).to_list_dict()[0]

            # expected checksum
            expected_checksum = hashlib.md5(file.read_bytes()).hexdigest()

            # check resource
            resource = self.client.read("resource", {"id": resp["id"]}).to_list_dict()[0]
            self.assertEqual(file.name, resource["name"])
            self.assertEqual("base64 encoded file", resource["description"])
            self.assertEqual(expected_checksum, resource["filechecksum"])


if __name__ == "__main__":
    unittest.main()
