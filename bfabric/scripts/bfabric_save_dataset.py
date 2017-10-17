#!/usr/bin/python

import sys
from bfabric import Bfabric

if __name__ == "__main__":
    bfapp = Bfabric()
    obj = {}
    obj['name'] = 'test dataset by CP'
    obj['projectid'] = 1000
    obj['attribute'] = [ {'name':'attr1', 'position':1},
        {'name':'attr2', 'position':2} ]

    obj['item'] = [ {'field':[ {'value': 1, 'attributeposition':1}, {'value': 1,  'attributeposition':2 } ], 'position':1}]
    print obj
    endpoint = 'dataset'
    res = bfapp.save_object(endpoint=endpoint, obj=obj)
    print res
