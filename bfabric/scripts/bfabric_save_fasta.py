#!/usr/bin/python

import sys
import os
import hashlib
from bfabric.utilities.utilities import save_fasta

if __name__ == "__main__":

    try:
        print
        "reading stdin"
        description = sys.stdin.read()
    except:
        print
        "reading from stdin failed."
        raise
    workunit = save_fasta(sys.args[1], sys.args[2], description_resource=description)

exit(0)

    description = """
Database created with prozor:
    resDB <- prozor::create_fgcz_fasta_db(databasedirectory, revLab = NULL)
where databasedirectory was prepared according to https://fgcz-intranet.uzh.ch/tiki-index.php?page=SOPrequestFASTA.
name: p3562_Anabaena_PCC_7120_d_20200525.fasta
annotation:
aa|p3562_Anabaena_PCC_7120|20200525 sequence download from https://www.uniprot.org/proteomes/UP000002483
nr sequences: 12663
 length summary:
    Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
     6.0   141.0   256.0   321.1   409.5  4936.0 
 AA frequencies:
     [,1]
 A 323401
 B     10
 C  42511
 D 195106
 E 251080
 F 159012
 G 275084
 H  73716
 I 278328
 K 195282
 L 443032
 M  72106
 N 187778
 P 187379
 Q 225268
 R 204535
 S 266676
 T 236048
 V 267610
 W  56806
 X     22
 Y 124790
 Z      6
 """
    ## save_fasta(projectid=sys.argv[1], fasta_file=sys.argv[2], description=description)

    workunit = save_fasta(projectid=3562,
                          fasta_file="C:/Users/wewol/Dropbox/DataAnalysis/p3562/fasta_db/p3562_Anabaena_PCC_7120_d_20200525.fasta",
                          description_resource=description,
                          description_workunit=description)
    exit(0)


# python bfabric_read.py workunit id  579682