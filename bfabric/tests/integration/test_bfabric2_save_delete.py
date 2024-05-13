from typing import Tuple
import unittest

from bfabric import BfabricAPIEngineType, Bfabric
from bfabric.bfabric import get_system_auth
from bfabric.experimental.multi_query import MultiQuery


def _find_delete_existing_objects_by_name(b: Bfabric, endpoint: str, name_list: list) -> Tuple[list, list]:
    """
    Checks if workunits with requested names exist. Attempts to delete the existing workunits

    :param b:          Bfabric instance
    :param endpoint:   Endpoint
    :param name_list:  List of names to check
    :return: Subset of workunit names that are found to exist, and deletion reports for those workunits
    """

    # 1. Check which objects exist
    objs_exist = MultiQuery(b).exists(endpoint, "name", name_list)
    objs_exist_names = [name for i, name in enumerate(name_list) if objs_exist[i]]

    if len(objs_exist_names) == 0:
        print("No", endpoint, "exists")
        return [], []
    else:
        print("Already exist:", objs_exist_names)

        ids_to_delete = []
        for name in objs_exist_names:
            # 2.1 Get IDs of all existing workunits
            response_dict = b.read(endpoint, {"name": name}).to_list_dict()
            ids_this = [r["id"] for r in response_dict]

            print("--", name, "exist with ids", ids_this)
            ids_to_delete += ids_this

        # Delete
        delete_response_dict = b.delete(endpoint, ids_to_delete).to_list_dict()
        print("Deletion results:", delete_response_dict)

        return objs_exist_names, delete_response_dict


class BfabricTestSaveDelete(unittest.TestCase):
    def setUp(self):
        self.config, self.auth = get_system_auth(config_env="TEST")

    def _save_delete_workunit(self, b: Bfabric, verbose: bool = False) -> None:
        """
        Integration test. Attempts to create some work units, then delete them.
        - We check whether, after creation, the workunits with the target names are found in the API,
            and the control workunit is not found (because it is not created)
        - We check whether the deletion of the created workunits is successful

        :param b:        BFabric Instance
        :param verbose:  Verbosity
        :return:
        """

        endpoint = "workunit"
        workunit_names = ["MewThePokemon", "TomMGM", "MinkyLeChat"]
        fake_name = "SpikeTheDog"
        all_names = workunit_names + [fake_name]

        # 1. Find and delete any workunits with these names, if they already exist
        print("Phase 1: Make sure to clean up workunits with target names, if they somehow already exist")
        _find_delete_existing_objects_by_name(b, endpoint, all_names)

        # 2. Create some workunits
        print("Phase 2: Creating the target units")
        new_ids = []
        for name in workunit_names:
            workunit1 = {"name": name, "applicationid": 2, "description": "is warm and fluffy", "containerid": 3000}
            response = b.save("workunit", workunit1).to_list_dict()  # We do the conversion to drop underscores in SUDS
            if verbose:
                print(response[0])

            self.assertEqual(len(response), 1, msg="Expected a single response from a single saved workunit")
            new_ids += [response[0]["id"]]

        # 3. Find and delete any workunits with these names, now that they have been created
        print("Phase 3: Finding and deleting the created work units, checking if they match expectation")
        found_names, deleted_responses = _find_delete_existing_objects_by_name(b, endpoint, all_names)

        self.assertEqual(
            found_names, workunit_names, msg="Expected the names found in the API to be the ones we just created"
        )
        for resp, trg_id in zip(deleted_responses, new_ids):
            self.assertEqual(len(resp), 1, msg="Deletion response format unexpected")
            self.assertIn("deletionreport", resp, msg="Deletion response format unexpected")
            self.assertEqual(
                resp["deletionreport"],
                "Workunit " + str(trg_id) + " removed successfully.",
                msg="Deletion response format unexpected",
            )

    def test_zeep(self):
        bZeep = Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.ZEEP)
        self._save_delete_workunit(bZeep, verbose=True)

    def test_suds(self):
        bSuds = Bfabric(self.config, self.auth, engine=BfabricAPIEngineType.SUDS)
        self._save_delete_workunit(bSuds, verbose=True)
