FROM buildpack-deps:stretch

ENV LANG C.UTF-8

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	python3-all python3-pip python3-setuptools python3-setuptools-scm tox \
	python3-requests python3-argcomplete python3-colorama python3-gnupg \
	debhelper dh-python devscripts build-essential fakeroot bash-completion \
	file git rsync zsh \
	asciidoc-base docbook docbook-xml xsltproc xmlto \
	&& apt-get clean

WORKDIR /tmp
ADD installPython.sh /tmp

RUN /tmp/installPython.sh 3.7.2 altinstall
RUN /tmp/installPython.sh 3.6.8 altinstall

RUN apt-get install -y libssl1.0-dev
RUN ./installPython.sh 3.4.9 altinstall
RUN apt-get install -y libssl-dev

RUN useradd -m -u 1000 leaf
