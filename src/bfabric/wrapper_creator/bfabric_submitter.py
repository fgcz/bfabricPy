from __future__ import annotations

import base64
from pathlib import Path

import yaml
from loguru import logger

from bfabric.bfabric import Bfabric
from bfabric.entities import ExternalJob, Executable
from bfabric.wrapper_creator.slurm import SLURM


class BfabricSubmitter:
    """
    the class is used by the submitter which is executed by the bfabric system.
    """

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
        client: Bfabric,
        externaljobid: int,
        user: str = "*",
        partition: str = "prx",
        nodelist: str = "fgcz-r-028",
        memory: str = "10G",
        scheduleroot: str = "/export/bfabric/bfabric/",
        scheduler: str = "GridEngine",
        script_dir: Path = Path("/home/bfabric/prx"),
    ) -> None:
        self._client = client
        self._executable_file_list = []

        self.partition = partition
        self.nodelist = nodelist
        self.memory = memory
        self.scheduleroot = scheduleroot
        self.scheduler = scheduler
        self.user = user
        self._script_dir = script_dir

        self.external_job = ExternalJob.find(id=externaljobid, client=client)
        self.workunit = self.external_job.workunit
        self.parameters = self.workunit.parameter_values
        self.application = self.workunit.application

        default_config = self.slurm_dict.get(self.application["name"], {})
        self.partition = self.parameters.get("partition", default_config.get("partition"))
        self.nodelist = self.parameters.get("nodelist", default_config.get("nodelist"))
        self.memory = self.parameters.get("memory", default_config.get("memory"))

        logger.debug(f"partition={self.partition}")
        logger.debug(f"nodelist={self.nodelist}")
        logger.debug(f"memory={self.memory}")
        logger.debug("__init__ DONE")

    # def submit_gridengine(self, script="/tmp/runme.bash", arguments=""):
    #    GE = gridengine.GridEngine(user=self.user, queue=self.queue, GRIDENGINEROOT=self.scheduleroot)
    #    print(script)
    #    print(type(script))
    #    resQsub = GE.qsub(script=script, arguments=arguments)
    #    self.B.logger(f"{resQsub}")

    def submit_slurm(self, script: str = "/tmp/runme.bash") -> None:
        slurm = SLURM(slurm_root=self.scheduleroot)
        logger.debug(script)
        logger.debug(type(script))
        res_slurm_batch = slurm.sbatch(script=script)
        logger.debug(f"{res_slurm_batch}")

    def compose_bash_script(self, configuration=None, configuration_parser=lambda x: yaml.safe_load(x)) -> str:
        """
        composes the bash script which is executed by the submitter (sun grid engine).
        as an argument it takes a configuration file, e.g., yaml, xml, json, or whatsoever, and a parser function.

        it returns a str object containing the code.

        :rtype : str
        """

        # assert isinstance(configuration, str)
        config = configuration_parser(configuration)

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
    echo "writing to output url failed!";
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
            job_notification_emails=self._client.config.job_notification_emails,
        )

        return _cmd_template

    def submitter_yaml(self) -> None:
        """
        implements the default submitter

        the function fetches the yaml base64 configuration file linked to the external job id out of the B-Fabric
        system. Since the file can not be staged to the LRMS as argument, we copy the yaml file into the bash script
        and stage it on execution the application.

        TODO(cp): create the output url before the application is started.

        return None
        """
        executables = Executable.find_by({"workunitid": self.workunit.id}, client=self._client).values()
        for executable in executables:
            if not executable["base64"]:
                continue

            logger.debug(f"executable = {executable}")
            content = base64.b64decode(executable["base64"].encode()).decode()
            logger.debug(content)
            _cmd_template = self.compose_bash_script(
                configuration=content, configuration_parser=lambda x: yaml.safe_load(x)
            )

            bash_script_file = Path(
                self._script_dir,
                f"workunitid-{self.workunit.id}_externaljobid-{self.external_job.id}"
                f"_executableid-{self.external_job.executable.id}.bash",
            )

            bash_script_file.write_text(_cmd_template)

            if self.scheduler == "GridEngine":
                raise NotImplementedError
                # self.submit_gridengine(bash_script_file)
            else:
                self.submit_slurm(str(bash_script_file))
            self._executable_file_list.append(str(bash_script_file))

        self._client.save("externaljob", {"id": self.external_job.id, "status": "done"})

    def get_job_script(self) -> list[str]:
        return self._executable_file_list
