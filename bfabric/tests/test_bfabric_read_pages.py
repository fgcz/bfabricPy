#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
unittest by <maria.derrico@fgcz.ethz.ch>
2022-09-21

Run verbose mode:
    python3 test_bfabric_read_pages.py -v

Input file groundtruth_pages.json: for each endpoint it is specified a value for the max_results parameter of the bfabric_read module, and as ground truth the length of the expected result, i.e. page_sixe*pages, where pages is the minimum number for which page_size*pages >= max_results

This test is expected to fail if the number of results per page get changed by B-Fabric. If this is the case, the page_size paramenter in the bfabric_read module need to be updated accordingly.
"""

import base64
import unittest
import bfabric
import os
import json
import time
import logging as log
import argparse

class TestBfabricReadEndPoints(unittest.TestCase):

    with open('groundtruth_pages.json') as json_file:
        groundtruth = json.load(json_file)

    bfapp = bfabric.Bfabric(verbose=False)

    def __init__(self, *args, **kwargs):
        super(TestBfabricReadEndPoints, self).__init__(*args, **kwargs)


    def read_pages(self, endpoint):
        self.assertIn(endpoint, self.groundtruth)
        for (query, max_results, groundtruth) in self.groundtruth[endpoint]:
            log.info(f"{endpoint}, {query}, {max_results}, {groundtruth}")
            start = time.time()
            res = self.bfapp.read_object(endpoint=endpoint, obj=query, max_results=max_results['max_results'])
            end = time.time()
            log.info("execution time: %f ", end-start)
            for gtattr, gtvalue in groundtruth.items():
                msg = "test for {} failed.".format(endpoint)
                self.assertEqual(gtvalue, len(res), msg)

 

    def test_user(self):
        self.read_pages('user')
    def test_container(self):
        self.read_pages('container')
    def test_project(self):
        self.read_pages('project')
    def test_application(self):
        self.read_pages('application')
    def test_sample(self):
        self.read_pages('sample')
    def test_workunit(self):
        self.read_pages('workunit')
    def test_resource(self):
        self.read_pages('resource')
    def test_executable(self):
        self.read_pages('executable')
    def test_annotation(self):
        self.read_pages('annotation')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='count', default=0)
    args = p.parse_args()
    if args.verbose:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.info("Verbose output.")
    else:
        log.basicConfig(format="%(levelname)s: %(message)s")

 
    suite = unittest.TestSuite()
    for entity in ['user', 'resource']:
        suite.addTest(TestBfabricReadEndPoints('test_{}'.format(entity)))

    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite )


