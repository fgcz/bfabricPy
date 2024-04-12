import pandas as pd

from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth
from bfabric.src.pandas_helper import list_dict_to_df

'''
Alpha-version of a system test, which would eventually make
basic queries to both Zeep and SUDS and test that the parsed responses match
'''


config, auth = get_system_auth()

def calc_query(engine):
    print("Sending query via", engine)
    b = Bfabric(config, auth, engine=engine)

    responseClass = b.read('user', {}, max_results=300, idonly=False, includedeletableupdateable=True)
    responseDict = responseClass.to_list_dict()
    return list_dict_to_df(responseDict)

def set_partition(a, b) -> None:
    aSet = set(a)
    bSet = set(b)
    print("Shared:", aSet.intersection(bSet))
    print("Unique(1):", aSet - bSet)
    print("Unique(2):", bSet - aSet)

# respDFSuds = calc_query(BfabricAPIEngineType.SUDS)
# respDFZeep = calc_query(BfabricAPIEngineType.ZEEP)
#
# respDFSuds.to_csv("tmp_suds.csv")
# respDFZeep.to_csv("tmp_zeep.csv")
respDFSuds = pd.read_csv("tmp_suds.csv")
respDFZeep = pd.read_csv("tmp_zeep.csv")

# Rename suds to remove underscores
respDFSuds.rename(columns={"_id": "id", "_classname": "classname"}, inplace=True)

sudsCols = list(sorted(respDFSuds.columns))
zeepCols = list(sorted(respDFZeep.columns))

set_partition(sudsCols, zeepCols)

for colName in sudsCols:
    if not respDFSuds[colName].equals(respDFZeep[colName]):
        print('-------', colName, '-------')
        # print('Suds', list(respDFSuds[colName]))
        # print('Zeep', list(respDFZeep[colName]))


print(respDFSuds['order'])
print(respDFZeep['order'])