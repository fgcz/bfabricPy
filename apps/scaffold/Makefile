# Christian Panse <cp@fgcz.ethz.ch>
# 201507

SCAFFOLDDRIVERPY=$(PWD)/fgcz_scaffold_create_xml_driver.py
SCAFFOLDDRIVERXMLTESTS=test_GeLC-MS.xml test_mudpit.xml test_nomudpit.xml

.PHONY : clean $(SCAFFOLDDRIVERXMLTESTS)

test: clean $(SCAFFOLDDRIVERXMLTESTS)
	@echo "\nYeah, all tests passed."


test_GeLC-MS.xml:
	@echo "\ntesting GeLC-MS ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=false --workunit 123 --gelcms=true \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem" \
	&& xmllint --noout --schema scaffold_simple.xsd $@

test_mudpit.xml:
	@echo "\ntesting mudpit ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

test_nomudpit.xml:
	@echo "\ntesting nomudpit ..."
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

clean:
	-rm -fv $(SCAFFOLDDRIVERXMLTESTS)
