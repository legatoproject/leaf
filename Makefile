# Makefile used to build leaf deliverables

# Setup directories
DIST:=dist
LEAF_TEST_TOX_ARGS?=
VENV_PYTHON_PATH?=python3

#.SILENT:
.PHONY: docker-build docker-test clean test sdist

all: sdist

clean:
	rm -rf $(MAN_OUTPUT_DIR) $(DIST)
	rm -rf .coverage coverage-report/ flake-report/ tests_*.xml build/

docker-image:
	docker build -t "leaf-test:latest" docker/

docker-test:
	docker run --rm \
		-v $(PWD):/mnt/leaf \
		-e LEAF_TEST_CLASS \
		-e LEAF_TEST_TOX_ARGS \
		-e LEAF_TEST_PYTEST_ARGS \
		leaf-test:latest \
		sh -c 'cp -R /mnt/leaf /leaf && cd /leaf && git clean -fdX && make clean test'

venv: requirements.txt
	virtualenv -p $(VENV_PYTHON_PATH) venv --no-site-packages
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	touch venv

test:
	chmod 700 src/tests/resources/gpg/
	tox $(LEAF_TEST_TOX_ARGS)

sdist:
	rm -rf $(DIST)
	python3 setup.py sdist

install:
	test -n "$(VIRTUAL_ENV)"
	python3 setup.py install
	python3 setup.py install_data

watch:
	test -n "$(VIRTUAL_ENV)"
	rerun -d src/leaf/ -p "**/*.py" -x "python3 setup.py install >/dev/null 2>&1"

