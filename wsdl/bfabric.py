#!/usr/bin/python
# -*- coding: latin1 -*-

"""
B-Fabric WSDL interface
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#   Nicola Palumbo <npalumbo@ethz.ch>
#
# Licensed under  GPL version 3
# $Id: bfabric.py 1620 2014-08-15 06:50:17Z cpanse $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Date: 2014-01-27 16:18:06 +0100 (Mon, 27 Jan 2014) $

from suds.client import Client
import hashlib
import os
import base64
import gridengine
import sys
import re

class Bfabric(object):
    """
    Implements read and save object methods for BFabric wsdl interface
    """
    bflogin='pfeeder'
    bfpassword='=YEHAYeah='
    webbase='http://fgcz-bfabric-demo.uzh.ch/bfabric'
    bfabricrc=dict()

    def _read_bfabric(self):
        bfabricfilename=os.environ['HOME'] + "/.bfabric"

        if not os.path.isfile(bfabricfilename):
            return
        try:
            with open(bfabricfilename) as myfile: 
                for line in myfile:
                    if not re.match("^#", line):
                        A = line.strip().replace("\"","").replace("'","").partition('=')
                        self.bfabricrc[A[0]]=A[2]
        except:
            raise

    def __init__(self, login=None, password=None, externaljobid=None):
        self._read_bfabric()

        if '_PASSWD' in self.bfabricrc.keys():
            password = self.bfabricrc['_PASSWD']

        if '_LOGIN' in self.bfabricrc.keys():
            login = self.bfabricrc['_LOGIN']

        if '_WEBBASE' in self.bfabricrc.keys():
            self.webbase=self.bfabricrc['_WEBBASE']

        if login:
            self.bflogin=login
        if password:
            self.bfpassword=password

        if not password or not login:
            print ("login or password missing")
            sys.exit(1)

    # TODO do a test if the login is working

    def read_object(self, endpoint, obj):
        """
        A generic methode which can connect to any endpoint, e.g., workunit, project,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint 
        for the "query".
        """ 
        QUERY=dict(login=self.bflogin, password=self.bfpassword, query=obj)
        try:
            client = Client("".join((self.webbase, '/', endpoint, "?wsdl")))
        except suds.WebFault, e:
            print e

        print client.service.read(QUERY)
        return getattr(client.service.read(QUERY), endpoint, None)

    def save_object(self, endpoint, obj, debug=None):
        """
        same as read_object above but uses the save method.
        """
        QUERY=dict(login=self.bflogin, password=self.bfpassword)
        QUERY[endpoint] = obj

        try:
            client = Client("".join((self.webbase, '/', endpoint, "?wsdl")))
        except suds.WebFault, e:
            print e

        if debug is not None:
            return client.service.save(QUERY)

        return getattr(client.service.save(QUERY), endpoint, None)

    def set_bfabric_credentials(self, login, password):
        self.bflogin=login
        self.bfpassword=password

    def set_bfabric_webbase(self, url):
        self.webbase=url

class BfabricFeeder(Bfabric):
    """ 
        this class is used for reporting 'resource' status 
    """
    def report_resource(self, resourceid):
        """
        this function determines the 'md5 checksum', 'the file size', 
        and set the status of the resource available.

        this is gonna executed on the storage host 

        """
        res = self.read_object('resource', { 'id': resourceid})[0] 

        if not hasattr(res, 'storage'):
            return -1

        storage = self.read_object('storage', { 'id': res.storage._id})[0]

        filename=storage.basepath + '/' + res.relativepath

        if os.path.isfile(filename):
            return self.save_object('resource', { 'id': resourceid,
                'weburl': None, 
                'size': os.path.getsize(filename), 
                'status': 'available',
                'filechecksum':hashlib.md5(open(filename, 'rb').read()).hexdigest()})

        return self.save_object('resource', { 'id': resourceid, 'status': 'failed'})

class BfabricExternalJob(Bfabric):
    """
    ExternalJobs can use logging.
    if you have a valid externaljobid use this class instead of
    using Bfabric.


    TODO check if an external job id is provided
    """
    externaljobid=None

    def __init__(self, login=None, password=None, externaljobid=None):
        super (BfabricExternalJob, self).__init__(login, password)
        if not externaljobid:
            print "Error: no externaljobid provided."
            sys.exit(1)
        else:
            self.externaljobid=externaljobid

    def logger(self, msg):
        if self.externaljobid:
            super (BfabricExternalJob, self).save_object('externaljob', { 'id': self.externaljobid, 'logthis': str(msg)}) 
        else:
            print str(msg)
    
    def save_object(self, endpoint, obj, debug=None):
        res = super (BfabricExternalJob, self).save_object(endpoint, obj, debug)
        self.logger('saved ' + endpoint + '=' + str(res))
        return res

    def get_workunitid_of_externaljob(self):
        res=self.read_object('externaljob', {'id': self.externaljobid})[0]
        workunit_list = filter(lambda x:x[0]=='cliententityid', res)
        return workunit_list[0][1] if workunit_list else None

    def get_executable_of_externaljobid(self):
        """ 
        It takes as input an `externaljobid` and fetches the the `executables` 
        out of the bfabric system using wsdl into a file.       
        returns a list of executables. 

        todo: this function should check if base64 is provided or
        just a program.
        """
        workunitid=self.get_workunitid_of_externaljob()
        if workunitid is None:
            return None

        executables=list()
        for executable in self.read_object(endpoint='executable', obj={'workunitid': workunitid}):
            if hasattr(executable, 'base64'):
                executables.append(executable)

        return executables if len(executables) > 0 else None

class BfabricSubmitter(BfabricExternalJob, gridengine.GridEngine):
    """
    the class is used by the submitter which is executed by the bfabric system.
    """
    def __init__(self, login=None, password=None, externaljobid=None, 
        user='*', queue="PRX@fgcz-s-021", GRIDENGINEROOT='/usr/local/GE2011'):

        gridengine.GridEngine.__init__(self, user=user, queue=queue, GRIDENGINEROOT=GRIDENGINEROOT)
        BfabricExternalJob.__init__(self, login=login, password=password, externaljobid=externaljobid)
        
    def submit(self, script):
        resQsub = super (BfabricSubmitter, self).qsub(script)
        self.logger(resQsub)

class BfabricWrapperCreator(BfabricExternalJob):
    """
    the class is used for the wrapper_creator which is executed by the bfabtic system
    """
    def uploadGridEngineScript(self, para={'INPUTHOST':'fgcz-s-021.uzh.ch'}):
        """
        the methode creates and uploads an executebale.  
        """
        _cmd_template = """#!/bin/bash
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Id: bfabric.py 1620 2014-08-15 06:50:17Z cpanse $
#$ -e {1}
#$ -o {2}

set -e
set -o pipefail


# debug
hostname
uptime
echo $0
pwd

# variables to be set by the wrapper_creator executable
{0}


# create output directory
ssh $SSHARGS $OUTPUTHOST "mkdir -p $OUTPUTPATH" || exit 1

# staging input and output data and proc
ssh $SSHARGS $INPUTHOST "cat $INPUTPATH/$INPUTFILE" \\
| $APPLICATION \\
| ssh $SSHARGS $OUTPUTHOST "cat > $OUTPUTPATH/$OUTPUTFILE \\
    && /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID \\
    && /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID" \\
|| exit 1

exit 0
""".format("\n".join(sorted([ '%s="%s"' % (key, info) for key, info in para.iteritems() ])), para['STDERR'], para['STDOUT'])

        resExecutable = self.save_object('executable', { 'name': os.path.basename(para['APPLICATION']) + "_executable", 
            'context': 'WORKUNIT', 
            'parameter': None, 
            'description': "This script should run as 'bfabric' user in the FGCZ compute infrastructure.", 
            'workunitid': para['WORKUNITID'],
            'base64': base64.b64encode(_cmd_template),
            'version': 0.2})

        return (resExecutable)

if __name__ == "__main__": 
    pass
