#!/usr/bin/env python

# -*- coding: latin1 -*-

"""
python setup.py test && echo $?
"""

from bfabric import Bfabric
import unittest



class TestLogin(unittest.TestCase):
    """
    run
        python -m unittest -v bfabric

    """

    def setUp(self):
        pass

    def test_login(self):
        bfapp = Bfabric()

        # try to generate a resource
        res = bfapp.save_object('resource', {
            'name': 'test resource',
            'relativepath': "/tmp/test_resource.txt"})[0]

        self.assertTrue('errorreport' in res)
        self.assertTrue(res['errorreport'] == "No workunit is specified.")


if __name__ == "__main__":
    pass
