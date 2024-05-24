#!/usr/bin/env python3
# -*- coding: latin1 -*-
import sys
import bfabric
import json

if __name__ == "__main__":
    B = bfabric.Bfabric(verbose=False)
    obj = {}
    obj["name"] = "qcloud2 annotaion test dataset by CP"
    obj["containerid"] = 3000
    obj["attribute"] = [
        {"name": "user_date", "position": 1},
        {"name": "user_email", "position": 2},
        {"name": "additional_information", "position": 3},
        {"name": "problems", "position": 4},
        {"name": "actions", "position": 5},
    ]
    obj["item"] = []

    with open("LUMOS_2.json") as json_file:
        d = json.load(json_file)

    for i in range(len(d)):
        try:
            problems = " | ".join([f"{j['name']} ({j['qccv']})" for j in d[i]["problems"]])
        except:
            problems = "-"

        try:
            actions = " | ".join([f"{j['name']} ({j['qccv']})" for j in d[i]["actions"]])
        except:
            actions = "-"

        it = {
            "field": [
                {"value": d[i]["user_date"], "attributeposition": 1},
                {"value": d[i]["user_email"], "attributeposition": 2},
                {"value": d[i]["additional_information"], "attributeposition": 3},
                {"value": problems, "attributeposition": 4},
                {"value": actions, "attributeposition": 5},
            ],
            "position": i + 1,
        }
        obj["item"].append(it)
    print(obj)
    # res = B.save_object(endpoint='dataset', obj=obj)
    # print (res[0])

"""
curl --location --request GET 'https://api.qcloud2.crg.eu/annotations?start_date=2019-04-01&end_date=2021-10-03&labsystem_name=LUMOS_2' --header "Authorization: Bearer ${ACCESSTOKEN}" > LUMOS_2.json
"""
