# Leaf Package Manager

Leaf is package management software written in Python 3, that manages downloading, installing and workspace configuration.


# Install

Python 3.5 or a newer version is required.

## Using Sierra Wireless released version

Installing the Leaf Debian package will automatically add the Sierra Wireless APT repository.

```sh
$ sudo apt install --yes wget
$ wget https://downloads.sierrawireless.com/tools/leaf/leaf_latest.deb -O /tmp/leaf.deb
$ sudo apt install --yes /tmp/leaf.deb
```

## Virtualenv install for development

Install dependencies:

```sh
$ sudo apt install --yes --no-install-recommends \
        python3-all python3-pip python3-virtualenv \
        git make
```

Clone the sources

```sh
$ git clone https://github.com/legatoproject/leaf
$ cd leaf
```

Create the virtualenv and install leaf for development

```sh
$ make venv
$ source venv/bin/activate
(venv) $ pip install -e .
```
> Note: Once installed using `-e`, leaf is installed in development mode, you don't need to reinstall it after you modify the code

# Running tests

## Using pytest

> You must be in a configured virtualenv, see "Install for development"

```sh
# Run all the tests
(venv) $ pytest
# Run only some tests
(venv) $ pytest src/tests/api
(venv) $ pytest -x src/tests/api/test_api_depends.py
```

## Using Tox

Tox can automatically run unit tests with supported python versions.

> Note: Tox is used to run all tests on multiple python environments, that means you need to have all supported python versions installed on your system to run Tox.

```sh
# Install tox inside a virtualenv
(venv) $ pip install tox
# or install tox on your system
$ sudo apt install tox
# then run tests
$ tox
# or a single python version
$ tox -e py37
```

## Using Docker

You can also run all tests using Tox inside a Docker container.

> You need to install Docker before, for example use `sudo apt install docker.io` on Debian Buster

```sh
# build the docker image
$ make docker-image
# run tests
$ make docker-test
```

You can also use the docker command line to tweak the arguments:

```sh
# Only run test using python37 with coverage and code analysis
$ export TOXENV=clean,py37,coverage,flake8
$ docker run --rm --volume $PWD:/src:ro \
        -e GIT_CLEAN=1 \
        -e TOXENV \
        multipy:leaf --alwayscopy -- -n 4 src/tests/api
```

You can tweak the tests with:
 - `TOXENV`: env variable to overide the list of Tox environments to execute, `clean`,`py37`, `coverage` and `flake8` in the previous example
 - `TOX_SKIP_ENV`: regular expression to filter down from running tox environments
 - Tox arguments: `--alwayscopy` in the previous example (Tox args are *before* the `--`)
 - Pytest arguments: `-n 4 -x src/tests/api` in the previous example (Tox args are *after* the `--`)
