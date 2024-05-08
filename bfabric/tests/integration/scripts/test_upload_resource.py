import contextlib
import datetime
import hashlib
import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from bfabric.bfabric2 import Bfabric
from bfabric.scripts.bfabric_upload_resource import bfabric_upload_resource
from bfabric.tests.integration.integration_test_helper import DeleteEntities


class TestUploadResource(unittest.TestCase):
    def setUp(self):
        self.client = Bfabric.from_config(config_env="TEST", verbose=True)
        self.delete_results = DeleteEntities(client=self.client, created_entities=[])
        self.addCleanup(self.delete_results)
        self.container_id = 3000

        self.ts = datetime.datetime.now().isoformat()

    def _create_workunit(self):
        # create workunit
        workunit = self.client.save(
            "workunit", {"containerid": self.container_id, "name": f"Testing {self.ts}", "applicationid": 1}
        ).to_list_dict()[0]
        self.delete_results.created_entities.append(("workunit", workunit["id"]))
        return workunit["id"]

    def test_upload_resource(self):
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            file = work_dir / "test.txt"
            file.write_text("Hello World!")

            workunit_id = self._create_workunit()

            # upload resource
            out_text = StringIO()
            with contextlib.redirect_stdout(out_text):
                bfabric_upload_resource(client=self.client, filename=file, workunit_id=workunit_id)
            resp = json.loads(out_text.getvalue())[0]

            # expected checksum
            expected_checksum = hashlib.md5(file.read_bytes()).hexdigest()

            # check resource
            resource = self.client.read("resource", {"id": resp["id"]}).to_list_dict()[0]
            self.assertEqual(file.name, resource["name"])
            self.assertEqual("base64 encoded file", resource["description"])
            self.assertEqual(expected_checksum, resource["filechecksum"])

    def test_upload_resource_when_already_exists(self):
        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)
            file = work_dir / "test.txt"
            file.write_text("Hello World!")

            workunit_id = self._create_workunit()

            # upload resource
            out_text = StringIO()
            with contextlib.redirect_stdout(out_text):
                bfabric_upload_resource(client=self.client, filename=file, workunit_id=workunit_id)
            resp = json.loads(out_text.getvalue())[0]
            self.assertEqual(workunit_id, resp["workunit"]["id"])

            # upload resource again
            with self.assertRaises(RuntimeError) as error:
                bfabric_upload_resource(client=self.client, filename=file, workunit_id=workunit_id)

            self.assertIn("Resource with the specified attribute combination already exists", str(error.exception))


if __name__ == "__main__":
    unittest.main()
