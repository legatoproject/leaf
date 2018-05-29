# Leaf Package Manager

Leaf is package management software written in Python 3, that manages downloading, installing and workspace configuration.


## Prerequisites

Python 3.4 or a newer version.

Install dependencies:
```shell
$ sudo apt-get install python3 python3-requests python3-argcomplete
```

## Install

### Using Sierra Wireless Released Version

Add the *Sierra Wireless* official apt repository and install *leaf*:

```shell
$ echo "deb http://updatesite.sierrawireless.com/legato-spm/debian release/" | sudo tee /etc/apt/sources.list.d/sierra.list
$ sudo apt-get update
$ sudo apt-get install leaf
```

### Alternative Setup Using Python setup.py and Leaf sources

Install *leaf* on your system: using python standard *setup.py*

```shell
$ sudo apt-get install python3-setuptools
$ cd src/
$ sudo python3 setup.py
```

To install *leaf* only for your user:

```shell
$ sudo apt-get install python3-setuptools
$ cd src/
$ python3 setup.py --user
```

### Building Debian Package

Install tools to build Debian package:

```shell
$ sudo apt-get install debhelper dh-python devscripts build-essential fakeroot python3-all python3-requests python3-setuptools
```

Debian packages need to be signed and *leaf* package needs to be signed by *developerstudio@sierrawireless.com*.
To build your *leaf* package, generate a custom *gpg key* for *developerstudio@sierrawireless.com* (you only need to do this once):

```shell
$ make gpg
```

Build the package:

```shell
$ make deb
# to install the package:
$ make install
# or
$ sudo dpkg -i target/leaf_latest.deb
# then install eventually missing dependencies
$ sudo apt-get -f install
```



## Running tests

### Using Nose

You can run unit tests using your default *python3* version using *nose*:

```shell
$ sudo apt-get install python3-nose
$ make test
# or
$ cd src/ && python3 -m nose
```

### Using Tox

Tox can automatically run unit tests with supported python versions (3.4, 3.5 & 3.6).
If you have all supported python versions installed on your system, you can use tox to run unit tests:

```shell
$ sudo apt-get install tox
$ make test-tox
# or
$ cd src/ && tox
```


### Using Docker

You can also run all tests using Tox inside a Docker container. if you have docker configured.

```shell
# build the docker image
$ make docker-build
# run tests
$ make docker-test
```


## Usage

See `leaf --help` for more details.
