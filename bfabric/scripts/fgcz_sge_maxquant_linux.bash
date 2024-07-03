#!/bin/bash

# $HeadURL: https://fgcz-svn.uzh.ch/repos/fgcz/stable/bfabric/sgeworker/bin/fgcz_sge_maxquant_linux.bash $
# $Id: fgcz_sge_maxquant_linux.bash 8956 2018-07-03 14:39:22Z  $
# $Date: 2018-07-03 16:39:22 +0200 (Tue, 03 Jul 2018) $

# ApplicationL 224 MaxQuant
# https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-application.html?id=224&tab=details
# Christian Panse <cp@fgcz.ethz.ch>
# 20180623
# 20180625

#$ -q maxquantlinux
#$ -N MQ


set -x
YAML=$1
DUMP=$2

test -f $YAML || { echo "can not find $YAML"; exit 1; }

SGEAPPBIN=~bfabric/sgeworker/bin/

# CHECK REQUIREMENTS
test -x $SGEAPPBIN/fgcz_maxquant_wrapper.py || exit 1
test -f $SGEAPPBIN/mqpar_template.xml || exit 1

[ -s /home/bfabric/sgeworker/bin/fgcz_yaml2.bash ] \
&& . /home/bfabric/sgeworker/bin/fgcz_yaml2.bash $1 \
|| { echo "can not exec fgcz_yaml2.bash"; exit 1; }

STAMP=`/bin/date +%Y%m%d%H%M`.$$.$JOB_ID
SCRATCH="/scratch/MAXQUANT/WU$WORKUNITID/"
mkdir -p $SCRATCH || { echo "mkdir -p $SCRATCH failed"; exit 1; }

sleep 1;
qalter -N MQ_LFQ_WU$WORKUNITID $JOB_ID

cp -av $YAML "$SCRATCH/WU$WORKUNITID.yaml" \
  && cd $SCRATCH \
  && $SGEAPPBIN/fgcz_maxquant_wrapper.py -y WU$WORKUNITID.yaml -x WU$WORKUNITID.xml \
  && nice -19 mono /usr/local/MaxQuant/MaxQuant_1.6.2.3/MaxQuant/bin/MaxQuantCmd.exe WU$WORKUNITID.xml \
    ||  { echo "bfabric MAXQUANT application failed in '$SCRATCH'."; exit 1; }


cd $SCRATCH && zip -j output-WU$WORKUNITID.zip *.txt *.pdf *.sf3 *.xml *.yaml combined/txt/*.txt \
  && scp $SCRATCH/output-WU$WORKUNITID.zip $OUTPUTURL \
    || { echo "scp failed"; exit 1; }
bfabric_setResourceStatus_available.py $RESSOURCEID \
  && bfabric_setExternalJobStatus_done.py $EXTERNALJOBID

cp -v $SCRATCH/*.yaml $SCRATCH/combined/ \
  && cd $SCRATCH/combined/txt/ \
  && R -e "library(SRMService); SRMService::fgcz_render_One2OneReport()" \
  && test -f fgcz_MQ_QC_report.pdf \
  && bfabric_upload_resource.py `pwd`/fgcz_MQ_QC_report.pdf $WORKUNITID || { echo "generation / upload fgcz_MQ_QC_report resource failed"; }

bfabric_upload_resource.py $SCRATCH/combined/txt/proteinGroups.txt $WORKUNITID || { echo "upload proteinGroups.txt resource failed"; }
bfabric_upload_resource.py $SCRATCH/combined/txt/parameters.txt $WORKUNITID || { echo "upload parameters.txt resource failed"; }

cd $SCRATCH/combined/proc \
  && echo "library(lattice); S <- read.table('#runningTimes.txt', header=T, sep='\t'); pdf('specs.pdf', 8, 6);barchart(~ Running.time..min. | Job, data=S[S\$Running.time..min.>30,], layout=c(1,3), ylab='numThreads'); dev.off()" \
  | R --no-save \
  && bfabric_upload_resource.py $SCRATCH/combined/proc/specs.pdf $WORKUNITID || { echo "upload specs.pdf resource failed"; }

echo $?
set +x
exit 0
