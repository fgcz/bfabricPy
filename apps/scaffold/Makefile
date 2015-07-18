# Christian Panse <cp@fgcz.ethz.ch>
# 201507
SCAFFOLDDRIVERPY=$(PWD)/fgcz_scaffold_create_xml_driver.py
SCAFFOLDDRIVERXML=test_GeLC-MS.xml test_mudpit.xml test_nomudpit.xml

test_all: $(SCAFFOLDDRIVERXML)
clean:
	-rm -fv $(SCAFFOLDDRIVERXML)

test_GeLC-MS.xml:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=false --workunit 123 --gelcms=true \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem" \
	&& xmllint --noout --schema scaffold_simple.xsd $@

test_mudpit.xml:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

test_nomudpit.xml:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVERPY) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| tee $@ \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"
