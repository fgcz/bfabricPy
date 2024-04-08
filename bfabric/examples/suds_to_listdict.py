from bfabric import bfabric
from bfabric.src.suds_format import suds_to_json
from typing import List


def read_shallow(b: bfabric.Bfabric, endpoint: str, obj: dict) -> List[dict]:
    response = b.read_object(endpoint=endpoint, obj=obj, plain=True)
    responseDict = suds_to_json(response)
    return responseDict[endpoint]

b = bfabric.Bfabric()
resLstDict = read_shallow(b, 'user', {'login': 'fomins'})

print(resLstDict)