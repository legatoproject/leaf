# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=$(PWD)/output

#.SILENT:
.PHONY: init all debArchive zipArchive clean test

all: init test debArchive zipArchive

init:
	mkdir -p $(OUTPUT)

test: 
	python3 -m nose --with-xunit
	cp nosetests.xml $(OUTPUT)/

clean:
	rm -Rf	output \
			packaging/leaf \
			packaging/debian/debhelper-build-stamp \
			packaging/debian/files \
			packaging/debian/leaf.debhelper.log \
			packaging/debian/leaf.substvars \
			packaging/debian/leaf/ \
			leaf_*.*

debArchive:
	rm -Rf packaging/leaf
	mkdir packaging/leaf
	cp -a leaf.py packaging/leaf/
	(cd packaging; debuild -b)
	mv leaf_*.* $(OUTPUT)
	(cd $(OUTPUT); zip leafDeb.zip *.deb *.changes)

zipArchive:
	mkdir -p $(OUTPUT)
	(cd src; zip -r $(OUTPUT)/leaf.zip *)
