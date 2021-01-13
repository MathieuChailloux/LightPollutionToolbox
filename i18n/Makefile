
FILES=$(shell find .. -name *.py)# -not -path "../algs/*")
TOOL=LightPollutionToolbox

.PHONY: update release

update:
	echo 'update $(TOOL)'
	pylupdate5 $(FILES) -ts '$(TOOL)_en.ts'
	pylupdate5 $(FILES) -ts '$(TOOL)_fr.ts'

release:
	echo "release"
	lrelease '$(TOOL)_en.ts' -qm '$(TOOL)_en.qm'
	lrelease '$(TOOL)_fr.ts' -qm '$(TOOL)_fr.qm'
