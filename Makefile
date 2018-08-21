# Makefile used to build leaf deliverables

# Setup directories
DIST:=dist
MAN_OUTPUT_DIR?=resources/man
MAN_INPUT_DIR?=doc/manpages
LEAF_TEST_CLASS?=
LEAF_TEST_TOX_ARGS?=

#.SILENT:
.PHONY: docker-build docker-test clean test sdist manpages

all: manpages sdist

clean:
	rm -rf $(MAN_OUTPUT_DIR) $(DIST)

manpages:
	rm -rf $(MAN_OUTPUT_DIR)
	mkdir -p $(MAN_OUTPUT_DIR)/man1
	./doc/manpages/mkman.sh $(MAN_INPUT_DIR) $(MAN_OUTPUT_DIR)/man1

docker-image:
	docker build -t "leaf-test:latest" docker/

docker-test:
	TMP_WORK_DIR=`mktemp -d -p /tmp leaf-docker-test.XXXXXX` && \
	chmod 777 $$TMP_WORK_DIR && \
	docker run --rm \
		--user 1000 \
		-v $(PWD):/src/leaf \
		-v $$TMP_WORK_DIR:/tmp/leaf \
		-e LEAF_TEST_CLASS="$(LEAF_TEST_CLASS)" \
		-e LEAF_TEST_TOX_ARGS="$(LEAF_TEST_TOX_ARGS)" \
		leaf-test:latest \
		sh -c 'cp -R /src/leaf /tmp && cd /tmp/leaf && git clean -fdX && make clean manpages test'

venv: requirements.txt
	virtualenv -p python3 venv --no-site-packages
	./venv/bin/pip install -r requirements.txt
	touch venv

test:
	LEAF_TEST_CLASS=$(LEAF_TEST_CLASS) tox $(LEAF_TEST_TOX_ARGS)

sdist:
	rm -rf $(DIST)
	python3 setup.py sdist
