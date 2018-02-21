# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=$(PWD)/output
SRC:=$(PWD)/src
DIST:=$(SRC)/dist

#.SILENT:
.PHONY: clean test deb archive all

all: clean test deb archive

clean:
	rm -rf $(SRC)/nosetests.xml $(OUTPUT) $(DIST)

test:
	echo > $(SRC)/nosetests.xml
	(cd $(SRC) && python3 -m nose --with-xunit)

deb:
	rm -rf $(DIST)
	$(PWD)/packaging/mkdeb.sh

archive: 
	mkdir $(OUTPUT)
	cp $(SRC)/nosetests.xml $(OUTPUT)/
	cp $(DIST)/*.deb        $(OUTPUT)/
	cp $(DIST)/*.changes    $(OUTPUT)/
	cp $(DIST)/*.tar.gz     $(OUTPUT)/
	cp $(OUTPUT)/*.deb      $(OUTPUT)/leaf_latest.deb
