SCAFFOLDDRIVER=$(PWD)/fgcz_scaffold_create_xml_driver.py
test_all: test_GeLC-MS test_mudpit test_nomudpit
test_GeLC-MS:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVER) --xtandem=false --mudpit=false --workunit 123 --gelcms=true \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

test_mudpit:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVER) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"

test_nomudpit:
	cat inputurl.txt \
	| $(SCAFFOLDDRIVER) --xtandem=false --mudpit=true --workunit 123 --gelcms=false \
	| grep --colour -E "analyzeAsMudpit|analyzeWithTandem"
