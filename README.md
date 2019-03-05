# Leaf Package Manager

Leaf is package management software written in Python 3, that manages downloading, installing and workspace configuration.


## Prerequisites

Python 3.4 or a newer version.

## Install

### Using Sierra Wireless released version

Add the *Sierra Wireless* official apt repository and install *leaf*:

```shell
$ echo "deb https://downloads.sierrawireless.com/tools/debian release/" | sudo tee /etc/apt/sources.list.d/legato-tools.list
$ sudo apt-get update
$ sudo apt-get install leaf
```

### Alternative install from sources

Install dependencies:

```shell
$ sudo apt-get install --no-install-recommends \
                       python3 python3-all python3-requests python3-argcomplete \
                       python3-setuptools python3-setuptools-scm python3-pytest \
                       asciidoc-base docbook docbook-xml xsltproc xmlto
```

Build the man pages:

```shell
$ make manpages
```

Install *leaf* on your system: using python standard *setup.py*

```shell
$ sudo python3 setup.py install
$ sudo python3 setup.py install_data
```

To install *leaf* only for your user:

```shell
$ python3 setup.py install --user
$ python3 setup.py install_data -d $HOME/.local/
```

### Alternative install in a *virtual env*

If you are not familiar with python virtualenv, see http://docs.python-guide.org/en/latest/dev/virtualenvs/

First if you don't have * virtualenv* installed:

```shell
$ sudo apt-get install python3-virtualenv
```

Then, create a virtualenv and install required packages:

```shell
$ make venv
# or
$ python3 -m virtualenv -p python3 venv --no-site-packages
$ source venv/bin/activate
$ pip install -r requirements.txt
$ pip install -r requirements-dev.txt
```

Finally, install leaf in your virtualenv:

```shell
$ ./setup.py install
$ ./setup.py install_data
```


### Troubleshooting

#### Ubuntu 14.04 LTS support

On Ubuntu 14.04 LTS, some library dependencies are not available at the correct version in the system
install. This will make leaf crashing on this distribution.
As an alternative, these libraries can be installed in user land:
```shell
$ sudo apt install python3-pip
$ pip3 install argcomplete --user
$ pip3 install setuptools --user --upgrade
```

## Running tests

### Using Nose

If you setup your virtualenv with the requirements, you can use pytest to run tests directly:

```shell
# First, install leaf in the venv
$ ./setup.py install
$ ./setup.py install_data
# Run all tests
$ pytest src/
# or a single class
$ pytest src/tests/api/test_api_filtering.py
```

### Using Tox

Tox can automatically run unit tests with supported python versions (3.4, 3.5 & 3.6).
If you have all supported python versions installed on your system, you can use tox to run unit tests:

```shell
# Install tox inside a virtualenv
$ pip install tox
# or install tox on your system
$ sudo apt-get install tox
# then run tests
$ tox
# or a single python version
$ tox -e py35
```

### Using Docker

You can also run all tests using Tox inside a Docker container. if you have docker configured.

```shell
# build the docker image
$ make docker-image
# run tests
$ make docker-test
```

You can tweak the tests with:
 - *LEAF_TEST_CLASS* to execute a single test class, for exemple `export LEAF_TEST_CLASS=src/tests/api`
 - *LEAF_TEST_TOX_ARGS* to tweak tox execution to select a specific python version, for example `export LEAF_TEST_TOX_ARGS="-e py35"`
 - *LEAF_TEST_PYTEST_ARGS* to tweak pytest execution, for example `export *LEAF_TEST_PYTEST_ARGS="-n 4"`


## Usage

See `leaf --help` of `leaf help` for more details.
