# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=output
TARGET:=target
DIST:=dist
MANDIR:=resources/man
LEAF_TEST_CLASS?=
LEAF_TEST_TOX_ARGS?=

#.SILENT:
.PHONY: ci docker-build docker-test clean test gpg sdist deb install uninstall manpages

all: manpages sdist deb

clean:
	rm -rf $(MANDIR) $(DIST) $(TARGET) $(OUTPUT)

manpages:
	rm -rf $(MANDIR)
	mkdir -p $(MANDIR)/man1
	./doc/manpages/mkman.sh doc/manpages/ $(MANDIR)/man1

ci: clean manpages test sdist deb
	rm -rf $(OUTPUT)
	mkdir -p $(OUTPUT)
	cp -a $(TARGET)/*       $(OUTPUT)
	cp -a nosetests_*.xml   $(OUTPUT)
	cp -a coverage-report_* $(OUTPUT)
	cp -a flake-report_*    $(OUTPUT)

docker-image:
	docker build -t "leaf-test:latest" docker/

docker-test:
	docker run --rm \
		--user 1000 \
		-v $(PWD):/src/leaf \
		-e LEAF_TEST_CLASS="$(LEAF_TEST_CLASS)" \
		-e LEAF_TEST_TOX_ARGS="$(LEAF_TEST_TOX_ARGS)" \
		leaf-test:latest \
		sh -c 'cp -a /src/leaf /tmp/leaf && cd /tmp/leaf && make manpages test'

gpg:
	gpg --batch --gen-key ./packaging/gpg-script

venv: requirements.txt
	virtualenv -p python3 venv --no-site-packages
	./venv/bin/pip install -r requirements.txt
	touch venv

test:
	LEAF_TEST_CLASS=$(LEAF_TEST_CLASS) tox $(LEAF_TEST_TOX_ARGS)

sdist:
	rm -rf $(DIST)
	python3 setup.py sdist

deb:
	rm -rf $(TARGET)
	./packaging/mkdeb.sh $(DIST)/leaf-*.tar.gz $(TARGET)

install:
	sudo apt install ./$(TARGET)/leaf_latest.deb

uninstall:
	sudo dpkg -r leaf

