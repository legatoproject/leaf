# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=$(PWD)/output
DIST:=$(PWD)/dist

#.SILENT:
.PHONY: clean test deb archive all

all: clean test deb archive

clean:
	rm -rf nosetests.xml $(OUTPUT) $(DIST)

test:
	echo > nosetests.xml
	python3 -m nose --with-xunit

deb:
	rm -rf $(DIST)
	$(PWD)/mkdeb.sh

archive: 
	mkdir $(OUTPUT)
	cp nosetests.xml $(OUTPUT)/
	cp $(DIST)/*.deb $(OUTPUT)/
	cp $(DIST)/*.changes $(OUTPUT)/
	cp $(DIST)/*.tar.gz $(OUTPUT)/
	cp $(OUTPUT)/*.deb $(OUTPUT)/leaf_latest.deb
