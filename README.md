# Leaf Package Manager

Leaf is package management software written in Python 3, that manages downloading, installing and workspace configuration.


## Prerequisites

Python 3.4 or a newer version.

## Install

### Using Sierra Wireless Released Version

Add the *Sierra Wireless* official apt repository and install *leaf*:

```shell
$ echo "deb http://updatesite.sierrawireless.com/legato-spm/debian release/" | sudo tee /etc/apt/sources.list.d/sierra.list
$ sudo apt-get update
$ sudo apt-get install leaf
```

### Alternative Setup Using Python setup.py and Leaf sources

Install dependencies:

```shell
$ sudo apt-get install --no-install-recommends \
                       python3 python3-requests python3-argcomplete \
                       python3-setuptools python3-all python3-nose \
                       asciidoc-base docbook docbook-xml xsltproc xmlto
```

Build the man pages:

```shell
$ make manpages
```

Install *leaf* on your system: using python standard *setup.py*

```shell
$ cd src/
$ sudo python3 setup.py
```

To install *leaf* only for your user:

```shell
$ cd src/
$ python3 setup.py install --user
$ python3 setup.py install_data --install-dir=$HOME/.local/
```

### Building Debian Package

Install dependencies:

```shell
$ sudo apt-get install --no-install-recommends \
                       python3 python3-requests python3-argcomplete \
                       python3-setuptools python3-all python3-nose \
                       debhelper dh-python devscripts build-essential fakeroot \
                       asciidoc-base docbook docbook-xml xsltproc xmlto
```

Debian packages need to be signed and *leaf* package needs to be signed by *developerstudio@sierrawireless.com*.
To build your *leaf* package, generate a custom *gpg key* for *developerstudio@sierrawireless.com* (you only need to do this once):

```shell
$ make gpg
```

Build the man pages:

```shell
$ make manpages
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
$ sudo apt-get install python3-nose python3-coverage
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

See `leaf --help` of `leaf help` for more details.


## Extending leaf

How to add an external command to leaf
- Add an executable into 'src/extensions/' folder
- The executable file name must start with 'leaf-'
  for example 'leaf-mycommand', 'mycommand' being the command name, runnable with 'leaf mycommand'
- The executable must handle '--description' argument to display some documentation 
  only the first line will be displayed in 'leaf --help'
  full documentation will be displayed with 'leaf mycommand --help' if implemented in your script
