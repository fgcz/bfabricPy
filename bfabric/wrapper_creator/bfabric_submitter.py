import base64

import yaml

import bfabric.wrapper_creator.gridengine as gridengine
import bfabric.wrapper_creator.slurm as slurm
from bfabric.wrapper_creator.bfabric_external_job import BfabricExternalJob


class BfabricSubmitter:
    """
    the class is used by the submitter which is executed by the bfabric system.
    """

    (G, B) = (None, None)

    workunitid = None
    workunit = None
    parameters = None
    execfilelist = []
    slurm_dict = {
        "MaxQuant_textfiles_sge": {"partition": "prx", "nodelist": "fgcz-r-033", "memory": "1G"},
        "fragpipe": {"partition": "prx", "nodelist": "fgcz-r-033", "memory": "256G"},
        "MaxQuant": {"partition": "maxquant", "nodelist": "fgcz-r-033", "memory": "4G"},
        "scaffold_generic": {"partition": "scaffold", "nodelist": "fgcz-r-033", "memory": "256G"},
        "MSstats dataProcess": {"partition": "prx", "nodelist": "fgcz-r-033", "memory": "64G"},
        "MaxQuant_sampleSizeEstimation": {"partition": "prx", "nodelist": "fgcz-r-028", "memory": "2G"},
        "ProteomeDiscovererQC": {"partition": "prx", "nodelist": "fgcz-r-035", "memory": "2G"},
    }

    def __init__(
        self,
        login=None,
        password=None,
        externaljobid=None,
        user="*",
        node="PRX@fgcz-r-018",
        partition="prx",
        nodelist="fgcz-r-028",
        memory="10G",
        SCHEDULEROOT="/export/bfabric/bfabric/",
        scheduler="GridEngine",
    ):
        """
        :rtype : object
        """
        self.B = BfabricExternalJob(login=login, password=password, externaljobid=externaljobid)
        self.partition = partition
        self.nodelist = nodelist
        self.memory = memory
        self.SCHEDULEROOT = SCHEDULEROOT
        self.user = user
        self.scheduler = scheduler

        print(self.B.auth.login)
        print(self.B.externaljobid)

        self.workunitid = self.B.get_workunitid_of_externaljob()

        try:
            self.workunit = self.B.read_object(endpoint="workunit", obj={"id": self.workunitid})[0]
        except:
            print("ERROR: could not fetch workunit while calling constructor in BfabricSubmitter.")
            raise

        try:
            self.parameters = [
                self.B.read_object(endpoint="parameter", obj={"id": x._id})[0] for x in self.workunit.parameter
            ]
        except:
            self.parameters = list()
            print("Warning: could not fetch parameter.")

        partition = [x for x in self.parameters if x.key == "partition"]
        nodelist = [x for x in self.parameters if x.key == "nodelist"]
        memory = [x for x in self.parameters if x.key == "memory"]
        application_name = self.B.get_application_name()

        if len(partition) > 0 and len(nodelist) > 0 and len(memory) > 0:
            self.partition = partition[0].value
            self.nodelist = nodelist[0].value
            self.memory = memory[0].value
        elif "queue" in [x.key for x in self.parameters] and application_name in self.slurm_dict:
            # Temporary check for old workunit previously run with SGE
            self.partition = self.slurm_dict[application_name]["partition"]
            self.nodelist = self.slurm_dict[application_name]["nodelist"]
            self.memory = self.slurm_dict[application_name]["memory"]
        else:
            pass

        print(f"partition={self.partition}")
        print(f"nodelist={self.nodelist}")
        print(f"memory={self.memory}")
        print("__init__ DONE")

    def submit_gridengine(self, script="/tmp/runme.bash", arguments=""):
        GE = gridengine.GridEngine(user=self.user, queue=self.queue, GRIDENGINEROOT=self.SCHEDULEROOT)

        print(script)
        print(type(script))
        resQsub = GE.qsub(script=script, arguments=arguments)

        self.B.logger(f"{resQsub}")

    def submit_slurm(self, script="/tmp/runme.bash", arguments=""):
        SL = slurm.SLURM(user=self.user, SLURMROOT=self.SCHEDULEROOT)

        print(script)
        print(type(script))
        resSbatch = SL.sbatch(script=script, arguments=arguments)

        self.B.logger(f"{resSbatch}")

    def compose_bash_script(self, configuration=None, configuration_parser=lambda x: yaml.safe_load(x)):
        """
        composes the bash script which is executed by the submitter (sun grid engine).
        as argument it takes a configuration file, e.g., yaml, xml, json, or whatsoever, and a parser function.

        it returns a str object containing the code.

        :rtype : str
        """

        # assert isinstance(configuration, str)

        try:
            config = configuration_parser(configuration)
        except:
            raise ValueError("error: parsing configuration content failed.")

        _cmd_template = """#!/bin/bash
# Maria d'Errico
# Christian Panse
# 2020-09-28
# 2020-09-29
# https://GitHub.com/fgcz/bfabricPy/
# Slurm
#SBATCH --partition={0}
#SBATCH --nodelist={11}
#SBATCH -n 1
#SBATCH -N 1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu={12}
#SBATCH -e {1}
#SBATCH -o {2}
#SBATCH --job-name=WU{10}
#SBATCH --workdir=/home/bfabric
#SBATCH --export=ALL,HOME=/home/bfabric

# Grid Engine Parameters
#$ -q {0}&{11}
#$ -e {1}
#$ -o {2}


set -e
set -o pipefail

export EMAIL="{job_notification_emails}"
export EXTERNALJOB_ID={3}
export RESSOURCEID_OUTPUT={4}
export RESSOURCEID_STDOUT_STDERR="{5} {6}"
export OUTPUT="{7}"
export WORKUNIT_ID="{10}"
STAMP=`/bin/date +%Y%m%d%H%M`.$$.$JOB_ID
TEMPDIR="/home/bfabric/prx"

_OUTPUT=`echo $OUTPUT | cut -d"," -f1`
test $? -eq 0 && _OUTPUTHOST=`echo $_OUTPUT | cut -d":" -f1`
test $? -eq 0 && _OUTPUTPATH=`echo $_OUTPUT | cut -d":" -f2`
test $? -eq 0 && _OUTPUTPATH=`dirname $_OUTPUTPATH`
test $? -eq 0 && ssh $_OUTPUTHOST "mkdir -p $_OUTPUTPATH"
test $? -eq 0 && echo $$ > $TEMPDIR/$$
test $? -eq 0 && scp $TEMPDIR/$$ $OUTPUT

if [ $? -eq 1 ];
then
    echo "writting to output url failed!";
    exit 1;
fi

# job configuration set by B-Fabrics wrapper_creator executable
# application parameter/configuration
cat > $TEMPDIR/config_WU$WORKUNIT_ID.yaml <<EOF
{8}
EOF



## interrupt here if you want to do a semi-automatic processing
if [ -x /usr/bin/mutt ];
then
    cat $0 > $TEMPDIR/$JOB_ID.bash

    (who am i; hostname; uptime; echo $0; pwd; ps;) \
    | mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID" $EMAIL \
        -a $TEMPDIR/$JOB_ID.bash $TEMPDIR/config_WU$WORKUNIT_ID.yaml
fi
# exit 0

# run the application
test -f $TEMPDIR/config_WU$WORKUNIT_ID.yaml && {9} $TEMPDIR/config_WU$WORKUNIT_ID.yaml


if [ $? -eq 0 ];
then
     ssh fgcz-r-035.uzh.ch "bfabric_setResourceStatus_available.py $RESSOURCEID_OUTPUT" \
     | mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID DONE" $EMAIL

     bfabric_save_workflowstep.py $WORKUNIT_ID
     bfabric_setExternalJobStatus_done.py $EXTERNALJOB_ID
     bfabric_setWorkunitStatus_available.py $WORKUNIT_ID
    echo $?
else
    echo "application failed"
     mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID failed" $EMAIL < /dev/null
     bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR $RESSOURCEID;
    exit 1;
fi

# should be available also as zero byte files
bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR


exit 0
""".format(
            self.partition,
            config["job_configuration"]["stderr"]["url"],
            config["job_configuration"]["stdout"]["url"],
            config["job_configuration"]["external_job_id"],
            config["job_configuration"]["output"]["resource_id"],
            config["job_configuration"]["stderr"]["resource_id"],
            config["job_configuration"]["stdout"]["resource_id"],
            ",".join(config["application"]["output"]),
            configuration,
            config["job_configuration"]["executable"],
            config["job_configuration"]["workunit_id"],
            self.nodelist,
            self.memory,
            job_notification_emails=self.B.config.job_notification_emails,
        )

        return _cmd_template

    def submitter_yaml(self):
        """
        implements the default submitter

        the function fetches the yaml base64 configuration file linked to the external job id out of the B-Fabric
        system. Since the file can not be stagged to the LRMS as argument, we copy the yaml file into the bash script
        and stage it on execution the application.

        TODO(cp): create the output url before the application is started.

        return None
        """

        # foreach (executable in external job):
        for executable in self.B.get_executable_of_externaljobid():
            self.B.logger(f"executable = {executable}")

            try:
                content = base64.b64decode(executable.base64.encode()).decode()
            except:
                raise ValueError("error: decoding executable.base64 failed.")

            print(content)
            _cmd_template = self.compose_bash_script(
                configuration=content, configuration_parser=lambda x: yaml.safe_load(x)
            )

            _bash_script_filename = f"/home/bfabric/prx/workunitid-{self.B.get_workunitid_of_externaljob()}_externaljobid-{self.B.externaljobid}_executableid-{executable._id}.bash"

            with open(_bash_script_filename, "w") as f:
                f.write(_cmd_template)

            if self.scheduler == "GridEngine":
                self.submit_gridengine(_bash_script_filename)
            else:
                self.submit_slurm(_bash_script_filename)
            self.execfilelist.append(_bash_script_filename)

        res = self.B.save_object(endpoint="externaljob", obj={"id": self.B.externaljobid, "status": "done"})

    def get_job_script(self):
        return self.execfilelist
