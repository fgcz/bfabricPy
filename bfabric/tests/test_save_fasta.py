import bfabric.scripts.bfabric_save_fasta as scripts



description = """
Database created with prozor: create_fgcz_fasta_db(databasedirectory = databasedirectory)
where databasedirectory was prepared according to https://fgcz-intranet.uzh.ch/tiki-index.php?page=SOPrequestFASTA 

FASTA name: p3553_935293_Yersinia_entomophaga_d_20200529.fasta
annotation:
aa|p3553_935293_Yersinia_entomophaga|20200529 https://www.uniprot.org/proteomes/UP000266744 3721 entries
nr sequences: 8417
 length summary:
    Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
     6.0   164.0   278.0   326.5   426.0  4660.0 
 AA frequencies:
     [,1]
 A 246347
 B     10
 C  35011
 D 140396
 E 161046
 F 102606
 G 209852
 H  59284
 I 159414
 K 124806
 L 294608
 M  69192
 N 111038
 P 120003
 Q 134680
 R 149653
 S 186538
 T 144020
 V 183144
 W  36110
 X     48
 Y  80076
 Z      6
"""

## save_fasta(projectid=sys.argv[1], fasta_file=sys.argv[2], description=description)

workunit = scripts.save_fasta(projectid=3553,
                      fasta_file="C:/Users/wewol/Dropbox/DataAnalysis/p65/p3553_935293_Yersinia_entomophaga_d_20200529.fasta",
                      description_resource=description,
                      description_workunit=description)
exit(0)

# python bfabric_read.py workunit id  579682
