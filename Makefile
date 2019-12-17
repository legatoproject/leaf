# Makefile used to build leaf deliverables

# Setup directories
LEAF_TEST_TOX_ARGS?=
VENV_PYTHON_PATH?=python3

#.SILENT:
.PHONY: docker-image docker-test clean test sdist dev

all: sdist

clean:
	rm -rf \
		.coverage* coverage-report/ \
		flake-report/ \
		tests_*.xml .pytest_cache/ .pytest_cache/ .tox/ \
		build/ dist/ .eggs/

docker-image:
	docker build \
		--build-arg APT_EXTRA_PACKAGES="gnupg" \
		-t multipy:leaf \
		https://github.com/essembeh/multipy.git

docker-test:
	chmod 700 src/tests/resources/gpg/
	docker run \
		--rm \
		--volume $(PWD):/src:ro \
		-e GIT_CLEAN=1 \
		-e TOXENV -e TOX_SKIP_ENV \
		multipy:leaf -- -n 4

venv: requirements.txt requirements-dev.txt
	python3 -m virtualenv -p $(VENV_PYTHON_PATH) venv --no-site-packages
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	touch venv

test:
	chmod 700 src/tests/resources/gpg/
	tox -- -n 4

sdist:
	python3 setup.py sdist

dev:
	test -n "$(VIRTUAL_ENV)"
	pip install -e.
