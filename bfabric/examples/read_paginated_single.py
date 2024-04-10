from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType

b = Bfabric(engine=BfabricAPIEngineType.SUDS)

responseClass = b.read('run', {}, max_results=None)
responseDict = responseClass.to_dict()

print(len(responseDict))