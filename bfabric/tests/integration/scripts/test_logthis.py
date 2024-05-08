import datetime
import unittest

from bfabric.bfabric2 import Bfabric
from bfabric.tests.integration.integration_test_helper import DeleteEntities


# TODO pending
@unittest.skip
class TestLogthis(unittest.TestCase):
    def setUp(self):
        self.client = Bfabric.from_config(config_env="TEST")
        self.delete_entities = DeleteEntities(client=self.client, created_entities=[])
        self.addCleanup(self.delete_entities)
        self.container_id = 3000
        self.ts = datetime.datetime.now().isoformat()

    def test_log(self):
        # create workunit
        workunit_id = self.client.save(
            "workunit", {"containerid": self.container_id, "name": f"Test {self.ts}", "applicationid": 1}
        ).to_list_dict()[0]["id"]
        self.delete_entities.created_entities.append(("workunit", workunit_id))

        # create external job
        external_job_id = self.client.save(
            "externaljob", {"workunitid": workunit_id, "action": "CREATE", "executableid": 1}
        ).to_list_dict()[0]["id"]
