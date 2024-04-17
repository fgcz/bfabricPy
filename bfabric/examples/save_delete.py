from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth

def find_delete_existing_objects_by_name(b: Bfabric, endpoint: str, name_list: list) -> None:
    # 1. Check which objects exist
    objs_exist = b1.exists(endpoint, 'name', name_list)
    objs_exist_names = [name for i, name in enumerate(all_names) if objs_exist[i]]

    if len(objs_exist_names) == 0:
        print("No", endpoint, "exists")
    else:
        print("Already exist:", objs_exist_names)

        ids_to_delete = []
        for name in enumerate(objs_exist_names):
            # 2.1 Get IDs of all existing workunits
            response_dict = b.read(endpoint, {'name': name}).to_list_dict()
            ids_this = [r['id'] for r in response_dict]

            print('--', name, 'exist with ids', ids_this)
            ids_to_delete += ids_this

        # Delete
        response_dict = b.delete(endpoint, ids_to_delete).to_list_dict()
        print('Deletion results:', response_dict)


# TODO: Check if works with ZEEP
# TODO: Why id=1525 matches random name queries, but is not deleteable???
# TODO: Adapt to tests
config, auth = get_system_auth()

b1 = Bfabric(config, auth, engine = BfabricAPIEngineType.SUDS)
# b2 = Bfabric(config, auth, engine = BfabricAPIEngineType.ZEEP)

endpoint = 'workunit'
workunit_names = ['MewThePokemon', 'TomMGM', 'MinkyLeChat']
fake_name = 'SpikeTheDog'
all_names = workunit_names + [fake_name]


# 1. Find and delete any workunits with these names, if they already exist
find_delete_existing_objects_by_name(b1, endpoint, all_names)

# 2. Create some workunits
for name in workunit_names:
    workunit1 = {'name': name, 'applicationid': 2, 'description': 'is warm and fluffy', 'containerid': 123}
    response = b1.save('workunit', workunit1)
    print(response.results[0])

# 3. Find and delete any workunits with these names, now that they have been created
find_delete_existing_objects_by_name(b1, endpoint, all_names)

# target_user_ids = [291792]
