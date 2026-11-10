from __future__ import annotations

import base64
import re
from pathlib import Path

import yaml
from loguru import logger

from bfabric.bfabric import Bfabric
from bfabric.entities import ExternalJob, Executable
from bfabric.wrapper_creator.slurm import SLURM

# Every value below is pasted into the job script, which bash and sbatch then interpret. The values come from
# workunit parameters and from the YAML executables of the workunit, both of which a B-Fabric user can write, so
# anything that is not plainly a name, a number or a path is refused instead of being quoted.
_SLURM_VALUE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_,.\-\[\]]*")
_LOG_PATH = re.compile(r"[A-Za-z0-9_./][A-Za-z0-9_@%+=,./-]*")
_OUTPUT_URL = re.compile(r"(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9.-]*:/[A-Za-z0-9_@%+=,./-]*")
_INTEGER = re.compile(r"[0-9]+")


def _checked(name: str, value: object, pattern: re.Pattern[str]) -> str:
    """Returns ``value`` as text if all of it matches ``pattern``.

    :raises ValueError: if it does not; nothing is written or submitted for such a job
    """
    text = str(value)
    if isinstance(value, bool) or pattern.fullmatch(text) is None:
        raise ValueError(f"Refusing to submit: {name} is not safe to place in a job script: {text[:80]!r}")
    return text


def _checked_output_list(outputs: object) -> str:
    if not isinstance(outputs, list) or not outputs:
        raise ValueError(f"Refusing to submit: application output is not a list of URLs: {str(outputs)[:80]!r}")
    return ",".join(_checked("application output", output, _OUTPUT_URL) for output in outputs)


class BfabricSubmitter:
    """
    the class is used by the submitter which is executed by the bfabric system.
    """

    slurm_dict = {
        "MaxQuant_textfiles_sge": {
            "partition": "prx",
            "nodelist": "fgcz-r-033",
            "memory": "1G",
        },
        "fragpipe": {"partition": "prx", "nodelist": "fgcz-r-033", "memory": "256G"},
        "MaxQuant": {"partition": "maxquant", "nodelist": "fgcz-r-033", "memory": "4G"},
        "scaffold_generic": {
            "partition": "scaffold",
            "nodelist": "fgcz-r-033",
            "memory": "256G",
        },
        "MSstats dataProcess": {
            "partition": "prx",
            "nodelist": "fgcz-r-033",
            "memory": "64G",
        },
        "MaxQuant_sampleSizeEstimation": {
            "partition": "prx",
            "nodelist": "fgcz-r-028",
            "memory": "2G",
        },
        "ProteomeDiscovererQC": {
            "partition": "prx",
            "nodelist": "fgcz-r-035",
            "memory": "2G",
        },
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
        job_configuration = config["job_configuration"]

        # The program comes from the application; a configuration naming another one was not written by the
        # wrapper creator.
        executable = str(self.application.executable["program"])
        if str(job_configuration["executable"]) != executable:
            raise ValueError(
                "Refusing to submit: the executable in the job configuration is not the application's program: "
                f"{str(job_configuration['executable'])[:80]!r}"
            )

        # base64 text holds no character that bash treats specially, and no line of it can be the delimiter:
        # each line is 76 characters long, or a shorter last line whose length is a multiple of 4.
        configuration_base64 = base64.encodebytes(configuration.encode()).decode().rstrip("\n")

        _cmd_template = """#!/bin/bash
# Maria d'Errico
# Christian Panse
# 2020-09-28
# 2020-09-29
# https://GitHub.com/fgcz/bfabricPy/
# Slurm
#SBATCH --partition={partition}
#SBATCH --nodelist={nodelist}
#SBATCH -n 1
#SBATCH -N 1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu={memory}
#SBATCH -e {stderr_url}
#SBATCH -o {stdout_url}
#SBATCH --job-name=WU{workunit_id}
#SBATCH --chdir=/home/bfabric
#SBATCH --export=ALL,HOME=/home/bfabric

set -euxo pipefail

# diagnostics
id
hostname
echo "${{PATH}}"
echo "${{LD_LIBRARY_PATH:-}}"
echo "${{MODULEPATH:-}}"
echo "${{LOADEDMODULES:-}}"
echo "${{SLURM_JOB_ID:-}}"
echo "${{TMPDIR:-}}"
echo "${{PYTHONPATH:-}}"
echo "${{R_LIBS:-}}"

export EMAIL="{job_notification_emails}"
export EXTERNALJOB_ID={external_job_id}
export RESSOURCEID_OUTPUT={resource_id_output}
export RESSOURCEID_STDOUT_STDERR="{resource_id_stderr} {resource_id_stdout}"
export OUTPUT="{output_list}"
export WORKUNIT_ID="{workunit_id}"
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
# (base64 encoded, so that no text in it is evaluated by this shell)
base64 -d > $TEMPDIR/config_WU$WORKUNIT_ID.yaml <<'EOF'
{configuration_base64}
EOF



## interrupt here if you want to do a semi-automatic processing
if [ -x /usr/bin/mutt ];
then
    cat $0 > $TEMPDIR/$EXTERNALJOB_ID.bash

    (who am i; hostname; uptime; echo $0; pwd; ps;) \
    | mutt -s "WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID" $EMAIL \
        -a $TEMPDIR/$EXTERNALJOB_ID.bash $TEMPDIR/config_WU$WORKUNIT_ID.yaml
fi
# exit 0

# Set the workunit status to processing
bfabric_setWorkunitStatus_processing.py $WORKUNIT_ID

# run the application
test -f $TEMPDIR/config_WU$WORKUNIT_ID.yaml && {executable} $TEMPDIR/config_WU$WORKUNIT_ID.yaml


if [ $? -eq 0 ];
then
     ssh fgcz-r-035.uzh.ch "bfabric_setResourceStatus_available.py $RESSOURCEID_OUTPUT" \
     | mutt -s "WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID DONE" $EMAIL

     bfabric_save_workflowstep.py $WORKUNIT_ID
     bfabric_setExternalJobStatus_done.py $EXTERNALJOB_ID
     bfabric_setWorkunitStatus_available.py $WORKUNIT_ID
    echo $?
else
    echo "application failed"
     mutt -s "WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID failed" $EMAIL < /dev/null
     bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR $RESSOURCEID;
     bfabric_setWorkunitStatus_failed.py $WORKUNIT_ID
    exit 1;
fi

# should be available also as zero byte files
bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR


exit 0
""".format(
            partition=_checked("partition", self.partition, _SLURM_VALUE),
            stderr_url=_checked("stderr url", job_configuration["stderr"]["url"], _LOG_PATH),
            stdout_url=_checked("stdout url", job_configuration["stdout"]["url"], _LOG_PATH),
            external_job_id=_checked("external_job_id", job_configuration["external_job_id"], _INTEGER),
            resource_id_output=_checked("output resource_id", job_configuration["output"]["resource_id"], _INTEGER),
            resource_id_stderr=_checked("stderr resource_id", job_configuration["stderr"]["resource_id"], _INTEGER),
            resource_id_stdout=_checked("stdout resource_id", job_configuration["stdout"]["resource_id"], _INTEGER),
            output_list=_checked_output_list(config["application"]["output"]),
            configuration_base64=configuration_base64,
            executable=executable,
            workunit_id=_checked("workunit_id", job_configuration["workunit_id"], _INTEGER),
            nodelist=_checked("nodelist", self.nodelist, _SLURM_VALUE),
            memory=_checked("memory", self.memory, _SLURM_VALUE),
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
