#!/bin/bash
# <{cp,sb}@fgcz.ethz.ch>
# 20130815
# 20150120


test $BASH_VERSINFO -lt 4 \
&& { echo "bash version less than 4"; exit 1; }

declare -A parameter=( ["mascot_db"]="fgcz_swissprot" ["verbose"]=false)
parameter["mgf"]="/srv/www/htdocs/p1000/Proteomics/LTQFT_1/cfortes_20120423_FritColum22cm_HPLC_TC18B/mgf__LTQ_FT_opt/20120423_11_fetuin400amol.mgf"
 

# $HeadURL: http://fgcz-svn.uzh.ch/repos/fgcz/stable/proteomics/bin/fgcz_mascot_custom_search.bash $
# $Id: fgcz_mascot_custom_search.bash 7122 2015-01-21 11:57:08Z cpanse $
# $Date: 2015-01-21 12:57:08 +0100 (Wed, 21 Jan 2015) $


# combine default mascot parameters and mgf to one asc file
# parameters: DB
# usage: fgcz_mascot_custom_search myMGF.mgf database_name myDAT.dat

function create_mascot_search_input(){

cat <<EOF
--
Content-Disposition: form-data; name="INTERMEDIATE"


--
Content-Disposition: form-data; name="FORMVER"

1.01
--
Content-Disposition: form-data; name="SEARCH"

MIS
--
Content-Disposition: form-data; name="PEAK"

AUTO
--
Content-Disposition: form-data; name="REPTYPE"

peptide
--
Content-Disposition: form-data; name="ErrTolRepeat"

0
--
Content-Disposition: form-data; name="SHOWALLMODS"


--
Content-Disposition: form-data; name="USERNAME"

QC Fetuin Search
--
Content-Disposition: form-data; name="COM"

MS/MS Test Search
--
Content-Disposition: form-data; name="DB"

$2
--
Content-Disposition: form-data; name="CLE"

Trypsin
--
Content-Disposition: form-data; name="PFA"

1
--
Content-Disposition: form-data; name="QUANTITATION"

None
--
Content-Disposition: form-data; name="TAXONOMY"

All entries
--
Content-Disposition: form-data; name="MODS"

Carbamidomethyl (C)
--
Content-Disposition: form-data; name="IT_MODS"

Oxidation (M)
--
Content-Disposition: form-data; name="TOL"

10
--
Content-Disposition: form-data; name="TOLU"

ppm
--
Content-Disposition: form-data; name="PEP_ISOTOPE_ERROR"

0
--
Content-Disposition: form-data; name="ITOL"

0.6
--
Content-Disposition: form-data; name="ITOLU"

Da
--
Content-Disposition: form-data; name="CHARGE"

2+, 3+ and 4+
--
Content-Disposition: form-data; name="MASS"

Monoisotopic


--
Content-Disposition: form-data; name="FORMAT"

Mascot generic
--
Content-Disposition: form-data; name="PRECURSOR"


--
Content-Disposition: form-data; name="INSTRUMENT"

LTQ-ORBI-Default
--
Content-Disposition: form-data; name="REPORT"

AUTO

--
Content-Disposition: form-data; name="FILE"; filename="test_search.mgf"
Content-Type: application/octet-stream


EOF

cat $1 

echo "--"
}

function search_mascot(){
# Mascot search ober SSH
    cat \
    | ssh -c arcfour -l $USER 130.60.81.18 "cd /usr/local/mascot/mascot_2_4/cgi \
        && /usr/local/mascot/mascot_2_4/cgi/nph-mascot.exe 1 -commandline -f /tmp/$$ \
        && cat /tmp/$$; \
        rm -f /tmp/$$"
}

function usage(){
    echo usage:
    echo "$0 -f <mascot_fasta_db> -m <mgf file>"
}


## MAIN
# read options
while getopts 'm:f:vhl' flag; 
do
    case "${flag}" in
        f) parameter["mascot_db"]=${OPTARG} ;;
        m) parameter["mgf"]=${OPTARG} ;;
        h) usage; exit 1 ;;
        l) ls /usr/local/mascot/sequence/; exit 1;;
        v) parameter['verbose']=true ;;
        *) error "Unexpected option ${flag}"; usage ;;
    esac
done

test -f ${parameter["mgf"]} || { echo "'$mgf' no such file."; exit 1; }
test -d /usr/local/mascot/sequence/${parameter["mascot_db"]} || { echo "'$mascot_db' not existing."; exit 1; }

echo "run mascot with the following parameters:"
for o in ${!parameter[*]};
do 
    echo "$o - ${parameter["$o"]}"; 
done


## RUN 
test -d /usr/local/mascot/mascot_2_4/cgi/ \
&& create_mascot_search_input ${parameter["mgf"]} ${parameter["mascot_db"]} \
| (cd /usr/local/mascot/mascot_2_4/cgi/ && ./nph-mascot.exe 1 -commandline)

echo $?

exit 0
