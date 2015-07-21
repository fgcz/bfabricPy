# exaple script executed by the bfabric submitter

```bash
cat externaljobid-45011_executableid-15136.bash
#!/bin/bash
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Id: bfabric.py 1888 2015-06-23 13:42:51Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch>
#$ -q PRX@fgcz-c-071
#$ -e /home/bfabric/sgeworker/logs/workunitid-134199_resourceid-200889.err
#$ -o /home/bfabric/sgeworker/logs/workunitid-134199_resourceid-200889.out

set -e
set -o pipefail

# debug
hostname
uptime
echo $0
pwd

# variables to be set by the wrapper_creator executable
APPLICATION="/usr/local/fgcz/proteomics/bin/fgcz_scaffold.bash --xtandem false --mudpit false --gelcms true --qmodel None"
EXTERNALJOBID="45010"
INPUTRESOURCEID="200624 200620 200618 200616"
INPUTURLS="( fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220928.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220930.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220929.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220925.dat )"
OUTPUTFILE="200889.sf3"
OUTPUTHOST="fgczdata.fgcz-net.unizh.ch"
OUTPUTPATH="/srv/www/htdocs//p1000/bfabric/Proteomics/scaffold_generic/2015/2015-07/2015-07-21//workunit_134199//"
RESSOURCEID="200889 200890 200891"
SSHARGS="-o StrictHostKeyChecking=no -c arcfour -2 -l bfabric -x"
STDERR="/home/bfabric/sgeworker/logs/workunitid-134199_resourceid-200889.err"
STDOUT="/home/bfabric/sgeworker/logs/workunitid-134199_resourceid-200889.out"
WORKUNITID="134199"

INPUTURLS=( fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220928.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220930.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220929.dat fgcz-s-018.uzh.ch:/usr/local/mascot//data/20150708/F220925.dat )

export RESSOURCEID
export INPUTURLS
export INPUTRESOURCEID

# create output directory
ssh $SSHARGS $OUTPUTHOST "mkdir -p $OUTPUTPATH" || exit 1
test $? -eq 0 || exit 1

SCRATCH=/scratch/$JOB_ID/


mkdir -p $SCRATCH
test $? -eq 0 || exit 1

echo "BEGIN COPY INPUT"
for (( i=0; ; i++ ))
do
    test -z "${INPUTURLS[$i]}" && break
    # TODO(cp@fgcz.ethz.ch): This is pain of the art.
    echo "${INPUTURLS[$i]}" >> $SCRATCH/inputurl.txt
    scp -c arcfour  ${INPUTURLS[$i]} $SCRATCH/`basename ${INPUTURLS[$i]}`
    test $? -eq 0 || { echo "scp failed with '${INPUTURLS[$i]}'"; exit 1; }
done
echo "END COPY INPUT"


$APPLICATION --scratch "$SCRATCH" --ssh "$OUTPUTHOST:$OUTPUTPATH/$OUTPUTFILE" \
&& /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID \
&& /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID \
|| { echo "application failed"; /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID; exit 1; }

cd $SCRATCH && rm -rf ./* || { echo "clean failed"; exit 1; }

exit 0
```
