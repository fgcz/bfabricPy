#!/usr/bin/python
# -*- coding: latin1 -*-

"""
A wrapper_creator for B-Fabric
Gets an external job id from B-Fabric
Creates an executable for the submitter

after successfull uploading the executables the wrapper creator creates an
externaljob
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/wrapper_creator2.py $
# $Id: wrapper_creator.py 1289 2014-01-31 06:49:24Z cpanse $ 

import os
import sys
import base64
import bfabric
import datetime

if __name__ == "__main__":
    externaljobid=-1
    if len(sys.argv) == 3 and sys.argv[1] == '-j' and int(sys.argv[2]) > 0:
        externaljobid = int(sys.argv[2])
    else:
        print "usage: " + sys.argv[0] + " -j <externaljobid>"    
        sys.exit(1)

    bfapp = bfabric.BfabricWrapperCreator(login='pfeeder', externaljobid=externaljobid)
    bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")

    workunitid = bfapp.get_workunitid_of_externaljob()

    if workunitid is None:
        print "ERROR: no workunit available for the given externaljobid."
        sys.exit(1)

    workunit = bfapp.read_object(endpoint='workunit', obj={'id': workunitid})

    if workunit is None:
        print "ERROR: no workunit available for the given externaljobid."
        sys.exit(1)

    # collects all required information out of B-Fabric to create an executable script
    workunit = workunit[0]
    application=bfapp.read_object('application', obj={'id':workunit.application._id})[0]
    executable=bfapp.read_object('executable', obj={'id': workunit.applicationexecutable._id})[0]
    project=workunit.project
    today = datetime.date.today()

    # merge all information into the executable script
    _outputStorage=bfapp.read_object('storage', obj={'id': application.storage._id})[0]
    _outputRelativePath = '/p' + str(project._id) + '/bfabric/' + str(application.technology).replace(' ', '_') + '/' + str(application.name).replace(' ', '_') + '/' + today.strftime('%Y/%Y-%m/%Y-%m-%d/') + 'workunit_' + str(workunitid) + '/'

    _logStorage=bfapp.read_object('storage', obj={'id': application.storage._id})[0]

    _cmd_applicationList = [ executable.program ]

    if getattr(workunit, "parameter", None) is not None:
        for parameter in workunit.parameter:
            parameter = bfapp.read_object('parameter', obj={'id':parameter._id, 'context':'APPLICATION'})
            if parameter:
                for p in parameter:
                    _cmd_applicationList.extend([" " , "--", p.key, " ", p.value])

    for resource in workunit.inputresource:
        _inputResource = bfapp.read_object('resource', {'id':resource._id})[0]
        _inputStorage = bfapp.read_object('storage', {'id':_inputResource.storage._id})[0]

        res0 = bfapp.save_object('resource', { 
            'name': application.name + ' resource', 
            'workunitid': workunit._id,
            'storageid': application.storage._id,
            'relativepath': _outputRelativePath})[0]

        _outputFilename = str(res0._id) + '.' + application.outputfileformat
        _gridengine_err_file = '/workunitid-' + str(workunit._id) + '_' + 'resourceid-' + str(res0._id) + '.err'
        _gridengine_out_file = '/workunitid-' + str(workunit._id) + '_' + 'resourceid-' + str(res0._id) + '.out'

        _res_err = bfapp.save_object('resource', { 
            'name': 'grid_engine_stderr', 
            'workunitid': workunit._id,
            'storageid': application.storage._id,
            'relativepath': _gridengine_err_file})[0]

        _res_out = bfapp.save_object('resource', { 
            'name': 'grid_engine_stdout', 
            'workunitid': workunit._id,
            'storageid': application.storage._id,
            'relativepath': _gridengine_out_file})[0]

        resNewExternaljob0 =bfapp.save_object('externaljob', {"workunitid": workunit._id, 
            'status': 'new', 
            'action': "WORKUNIT"})[0] 

        res1 = bfapp.save_object('resource', { 
            'id': res0._id, 
            'relativepath':  _outputRelativePath + '/' + _outputFilename})

        # upoload the ready to run script to B-Fabric as base64 encoded file
        _inputPath = '/'.join((str.split(str(_inputStorage.basepath) + str(_inputResource.relativepath), "/")[:-1]))
        _inputFile = str.split(str(_inputResource.relativepath), "/")[-1]

        resExecutable = bfapp.uploadGridEngineScript(para={'WORKUNITID':workunit._id,
            'EXTERNALJOBID':resNewExternaljob0._id,
            'RESSOURCEID': str(res0._id) + " " + str(_res_err._id) + " " + str(_res_out._id),
            'INPUTHOST': _inputStorage.host,
            'INPUTPATH': _inputPath,
            'INPUTFILE': _inputFile,
            'OUTPUTHOST': _outputStorage.host,
            'OUTPUTPATH': _outputStorage.basepath + _outputRelativePath + '/',
            'OUTPUTFILE': _outputFilename,
            'APPLICATION': ''.join((_cmd_applicationList)),
            'STDERR': _logStorage.basepath + _gridengine_err_file,
            'STDOUT': _logStorage.basepath + _gridengine_out_file,
	    'SSHARGS': "-o StrictHostKeyChecking=no -c arcfour -2 -l bfabric"
            })[0]

        resNewExternaljob1 =bfapp.save_object('externaljob', {"id": resNewExternaljob0._id, 'executableid': resExecutable._id })

    resExternaljob = bfapp.save_object(endpoint='externaljob', obj={'id':externaljobid, 'status':'done'})
