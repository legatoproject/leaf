# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=$(PWD)/output

#.SILENT:
.PHONY: all debArchive zipArchive clean

all: debArchive zipArchive

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
	mkdir -p $(OUTPUT)
	rm -Rf packaging/leaf
	cp -a src packaging/leaf
	(cd packaging; debuild -b)
	mv leaf_*.* $(OUTPUT)
	(cd $(OUTPUT); zip leafDeb.zip *.deb *.changes)

zipArchive:
	mkdir -p $(OUTPUT)
	(cd src; zip -r $(OUTPUT)/leaf.zip *)
