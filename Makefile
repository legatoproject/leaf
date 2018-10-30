# Makefile used to build leaf deliverables

# Setup directories
DIST:=dist
MAN_OUTPUT_DIR?=resources/man
MAN_INPUT_DIR?=doc/manpages
LEAF_TEST_TOX_ARGS?=

#.SILENT:
.PHONY: docker-build docker-test clean test sdist manpages

all: manpages sdist

clean:
	rm -rf $(MAN_OUTPUT_DIR) $(DIST)
	rm -rf .coverage coverage-report/ flake-report/ nosetests_*.xml build/

manpages:
	rm -rf $(MAN_OUTPUT_DIR)
	mkdir -p $(MAN_OUTPUT_DIR)/man1
	./doc/manpages/mkman.sh $(MAN_INPUT_DIR) $(MAN_OUTPUT_DIR)/man1

docker-image:
	docker build -t "leaf-test:latest" docker/

docker-test:
	docker run --rm \
		-v $(PWD):/src/leaf \
		-e LEAF_TEST_CLASS \
		-e LEAF_TEST_TOX_ARGS \
		leaf-test:latest \
		sh -c 'cp -R /src/leaf /tmp && cd /tmp/leaf && git clean -fdX && make clean manpages test'

venv: requirements.txt
	virtualenv -p python3 venv --no-site-packages
	./venv/bin/pip install -r requirements.txt
	touch venv

test:
	chmod 700 src/tests/gpg/
	tox $(LEAF_TEST_TOX_ARGS)

flake:
	tox -e clean,flake

sdist:
	rm -rf $(DIST)
	python3 setup.py sdist

install:
	test -n "$(VIRTUAL_ENV)"
	python3 setup.py install
	python3 setup.py install_data
