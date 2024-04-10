from bfabric.bfabric2 import Bfabric
from bfabric.src.suds_format import suds_asdict_recursive
from typing import List


def read_shallow(b: Bfabric, endpoint: str, obj: dict) -> List[dict]:
    response = b.read(endpoint, obj)
    response_dict = suds_asdict_recursive(response)
    return response_dict[endpoint]

b = Bfabric()
res_list_dict = read_shallow(b, 'user', {'login': 'fomins'})

print(res_list_dict)