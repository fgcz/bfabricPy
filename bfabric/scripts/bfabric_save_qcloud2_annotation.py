#!/usr/bin/env python3
# -*- coding: latin1 -*-
import sys
import bfabric
import json

if __name__ == "__main__":
    B = bfabric.Bfabric(verbose=False)
    obj = {}
    obj['name'] = 'qcloud2 annotaion test dataset by CP'
    obj['containerid'] = 3000
    obj['attribute'] = [ 
        {'name': 'user_date', 'position':1},
        {'name': 'user_email', 'position':2},
        {'name': 'additional_information', 'position':3},
        {'name': 'problems', 'position':4},
        {'name': 'actions', 'position':5}
    ]
    obj['item'] = []
 #{'user_date': '2021-06-22 17:06:19', 'user_email': 'paolo.nanni@fgcz.uzh.ch', 'additional_information': None, 'problems': [], 'actions': [{'name': 'Pre-column changed', 'qccv': 'TS:0000029'}]}
    #obj['item'] = [ {'field':[ {'value': 1, 'attributeposition':1}, {'value': 1,  'attributeposition':2 } ], 'position':1}]
    #obj['item'] = [ {'field':[ 
    #    {'value': '2021-06-22 17:06:19', 'attributeposition':1},
    #    {'value': 'paolo.nanni@fgcz.uzh.ch',  'attributeposition':2 },
    #    {'value': 'paolo.nanni@fgcz.uzh.ch',  'attributeposition':3 },
    #    {'value': 'paolo.nanni@fgcz.uzh.ch',  'attributeposition':4 },
    #    {'value': 'paolo.nanni@fgcz.uzh.ch',  'attributeposition':5 },
    #    {'value': 'paolo.nanni@fgcz.uzh.ch',  'attributeposition':6 }
    #    ], 'position':1}]

    with open('/home/cpanse/LUMOS_2.json') as json_file:
        d = json.load(json_file)

    for i in range(len(d)):
        try:
            problems = " | ".join([ "{} ({})".format(j['name'], j['qccv']) for j in d[i]['problems'] ])
        except:
            problems = '-'

        try:
            actions = " | ".join([ "{} ({})".format(j['name'], j['qccv']) for j in d[i]['actions'] ])
        except:
            actions = '-'

        it = {'field':[
        {'value': d[i]['user_date'], 'attributeposition':1},
        {'value': d[i]['user_email'], 'attributeposition':2},
        {'value': d[i]['additional_information'], 'attributeposition':3},
        {'value': problems, 'attributeposition':4},
        {'value': actions, 'attributeposition':5}
        ], 'position': i + 1}
        obj['item'].append(it)
    print(obj)
    res = B.save_object(endpoint='dataset', obj=obj)
    print (res[0])
