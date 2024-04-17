from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth
from bfabric.src.pandas_helper import list_dict_to_df


config, auth = get_system_auth()

b1 = Bfabric(config, auth, engine = BfabricAPIEngineType.SUDS)
b2 = Bfabric(config, auth, engine = BfabricAPIEngineType.ZEEP)

target_user_ids = [1,2,3,4,5, 12345]

response1 = b1.exists("user", target_user_ids)
response2 = b2.exists("user", target_user_ids)

print(response1)
print(response2)
