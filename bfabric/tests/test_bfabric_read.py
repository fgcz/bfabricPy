#!/usr/bin/env python3
# -*- coding: latin1 -*-

import sys
import bfabric
import pprint
from bfabric import Bfabric

import json
import yaml

if __name__ == '__main__':
    bfapp = Bfabric()

    pp = pprint.PrettyPrinter(depth=6)

    for i in range(1, 10):
        print("### query {}".format(i))
        res = bfapp.read_object(endpoint='workunit', obj={'id': 123456})
        print(res)
#   print (yaml.dump(res[0]['workunit']))

