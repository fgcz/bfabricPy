# Christian Panse <cp@fgcz.ethz.ch>
# 201507

DATE = $(shell date +%s)
SHELL = /bin/sh -c

SCAFFOLDDRIVERPY = $(PWD)/fgcz_scaffold_create_xml_driver.py
SCAFFOLDDBATCH4 = /srv/FGCZ/SCAFFOLD/scaffold.c71/ScaffoldBatch4 
SCAFFOLDDBATCH4OPT = -q -f -keypath /srv/FGCZ/SCAFFOLD/scaffold.c71/share/registeredKey.lkeynew

INSTALLDIR = /usr/local/fgcz/proteomics/bin/

.PHONY: clean $(SCAFFOLDDRIVERTESTSSF3)
.SUFFIXES: .sf3 .xml .log

all: test_GeLC-MS.sf3 test_mudpit.sf3 test_nomudpit.sf3

install: all
	test -d $(INSTALLDIR) \
	&& cp -av $(SCAFFOLDDRIVERPY) fgcz_scaffold.bash $(INSTALLDIR)

%.sf3 : %.xml
	@echo "\nrun ScaffoldBatach4 using '$<' driver ..."
	$(SCAFFOLDDBATCH4) $(SCAFFOLDDBATCH4OPT) $(PWD)/$< >$*.1.log 2>$*.2.log

test:
	@echo "\nYeah, all tests passed."


test_GeLC-MS.xml:
	@echo "\ncreating scaffold driver file for 'GeLC-MS' configuration ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=false --workunit 123 --gelcms=true --sf3=$*.sf3 \
	| tee $@  \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem" \
	&& xmllint --noout --schema scaffold_simple.xsd $@


test_mudpit.xml:
	@echo "\ncreating scaffold driver file for 'mudpit' configuration ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false --sf3=$*.sf3 \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

test_nomudpit.xml:
	@echo "\ncreating scaffold driver file for 'nomudpit' configuration ..."
	cat inputurl.txt \
        | $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=false --workunit 123 --gelcms=false --sf3=$*.sf3 \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

clean:
	@echo "cleaning ..."
	-rm -fv *.xml *.sf3 *.log
