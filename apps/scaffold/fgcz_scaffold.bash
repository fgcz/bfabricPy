#!/bin/bash

# Contact <{cp,jg}@fgcz.ethz.ch>

# $HeadURL: http://fgcz-svn.uzh.ch/repos/fgcz/stable/proteomics/bin/fgcz_scaffold.bash $
# $Id: fgcz_scaffold.bash 7552 2015-06-30 11:21:26Z cpanse $
# $Date: 2015-06-30 13:21:26 +0200 (Tue, 30 Jun 2015) $
# $Author: cpanse $

### cat inputurl.txt | ./prg --qmodel "" --mudpit true --tandem false --ssh bfabric@fgcz-s-021:/srv/www/htdocs/p1000/bfabric/... --scratch /scrach/999

echo "running '$0' ..."
echo "BASH_VERSINFO=$BASH_VERSINFO"
echo "RESSOURCEID=$RESSOURCEID"
echo "INPUTRESSOURCEID=$INPUTRESSOURCEID"
echo "INPUTURLS=$INPUTURLS"

test $BASH_VERSINFO -ge 4 || { echo "ERROR: bash version is less than 4"; exit 1; }

set -e
set -o pipefail

SSHOUTPUT=''
SCRATCH="/scratch/$$"
SCAFFOLDDRIVERPY=/usr/local/fgcz/proteomics/bin/fgcz_scaffold_create_xml_driver.py
SCAFFOLDDBATCH4=/srv/FGCZ/SCAFFOLD/scaffold.c71/ScaffoldBatch4
SCAFFOLDKEYPATH=/srv/FGCZ/SCAFFOLD/scaffold.c71/share/registeredKey.lkeynew

test -x $SCAFFOLDDBATCH4 \
|| { echo "ERROR: SCAFFOLDDBATCH4='$SCAFFOLDDBATCH4' cound not be found."; exit 1; }

test -x $SCAFFOLDDRIVERPY \
|| { echo "ERROR: SCAFFOLDDRIVERPY='$SCAFFOLDDRIVERPY'  is not available."; exit 1; }

test -f $SCAFFOLDKEYPATH \
|| { echo "ERROR: SCAFFOLDKEYPATH='$SCAFFOLDKEYPATH' scaffold key file is not available."; exit 1; }

cleanup(){
            cd $SCRATCH && rm  -fv ./* || { echo "cleanup failed"; exit 1; }
}

trap "{ echo 'trapped by return code $? (cleaning up) ...'; cleanup ; exit $?; }" EXIT


GELCMS="FALSE"
MUDPID="FALSE"
XTANDEM="FALSE"
QMODEL="None"
WORKUNIT=0

while [[ $# > 1 ]]
do
    key="$1"
    shift

    case $key in
        --qmodel)
            QMODEL="$1"
            shift
        ;;
        --mudpid)
            MUDPID="$1"
            shift
        ;;
        --gelcms)
            GELCMS="$1"
            shift
        ;;
        --xtandem)
            XTANDEM="$1"
            shift
        ;;
        --ssh) 
            SSHOUTPUT="$1"
            shift
        ;;
        --scratch)
            SCRATCH="$1"
            shift
        ;;
        *)
       # unknown option
       ;;
    esac
done
echo $GELCMS
echo $MUDPID
echo $XTANDEM
echo $SCRATCH
echo $SSHOUTPUT
echo $QMODEL
echo $WORKUNIT

# MAIN
cd $SCRATCH || { echo "cd into SCRATCH DIR failed"; exit 1; }      

ls \
| grep dat$ \
| $SCAFFOLDDRIVERPY  --xtandem=$XTANDEM --mudpit=$MUDPID --gelcms=$GELCMS --workunit $WORKUNIT --qmodel=$QMODEL \
| tee driver.xml \
|| { echo "fgcz_scaffold_create_xml_driver.py failed"; exit 1; }

$SCAFFOLDDBATCH4 -q -f -keypath $SCAFFOLDKEYPATH $PWD/driver.xml \
|| { echo "scaffold application failed"; exit 1; }

scp $SCRATCH/scaffold.sf3 $SSHOUTPUT || { echo "ERROR: copy output failed."; exit 1; }

sleep 3

exit 0
