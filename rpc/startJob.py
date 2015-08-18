__author__ = 'witold'

# /bin/python /path/to/this/file/startJob.py -j jobid
#

import xmlrpclib
import argparse

WORKFLOW_LOCATION="http://localhost:8000/"

parser = argparse.ArgumentParser(description='Start a job.')
parser.add_argument('-j', type=int, help='job id', dest="job_id")
args = parser.parse_args()

print args.job_id
proxy = xmlrpclib.ServerProxy(WORKFLOW_LOCATION)
print "3 is even: %s" % str(proxy.runJob(args.job_id))

