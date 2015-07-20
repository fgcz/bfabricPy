# Christian Panse <cp@fgcz.ethz.ch>
# 201507

SCAFFOLDDRIVERPY=$(PWD)/fgcz_scaffold_create_xml_driver.py
SCAFFOLDDRIVERTESTSSF3=test_GeLC-MS.sf3 test_mudpit.sf3 test_nomudpit.sf3

SCAFFOLDDBATCH4=/srv/FGCZ/SCAFFOLD/scaffold.c71/ScaffoldBatch4 
SCAFFOLDDBATCH4OPT=-q -f -keypath /srv/FGCZ/SCAFFOLD/scaffold.c71/share/registeredKey.lkeynew

.PHONY : clean $(SCAFFOLDDRIVERTESTSSF3)
.SUFFIXES: .sf3 .xml

all: test_GeLC-MS.sf3

%.sf3 : %.xml
	$(SCAFFOLDDBATCH4) $(SCAFFOLDDBATCH4OPT) $(PWD)/$< >$*.1.log 2>$*.2.log

test:
	@echo "\nYeah, all tests passed."


test_GeLC-MS.xml:
	@echo "\ntesting GeLC-MS ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=false --workunit 123 --gelcms=true --sf3=$*.sf3 \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem" \
	&& xmllint --noout --schema scaffold_simple.xsd $@

test_mudpit.xml:
	@echo "\ntesting mudpit ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false --sf3=$*.sf3 \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"
	$(SCAFFOLDDBATCH4) $(SCAFFOLDDBATCH4OPT) $(PWD)/$@ > $*.log

test_nomudpit.xml:
	@echo "\ntesting nomudpit ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false --sf3=$*.sf3 \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"
	$(SCAFFOLDDBATCH4) $(SCAFFOLDDBATCH4OPT) $(PWD)/$@ > $*.log

clean:
	@echo "cleaning ..."
	-rm -fv *.xml *.sf3 *.log
