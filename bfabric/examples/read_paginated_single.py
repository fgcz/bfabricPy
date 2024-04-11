from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth
from bfabric.src.pandas_helper import list_dict_to_df


config, auth = get_system_auth()

# b = Bfabric(config, auth, engine=BfabricAPIEngineType.SUDS)
b = Bfabric(config, auth, engine=BfabricAPIEngineType.ZEEP)

responseClass = b.read('user', {}, max_results=300)
responseDict = responseClass.to_list_dict()
responseDF = list_dict_to_df(responseDict)

print(responseDF)