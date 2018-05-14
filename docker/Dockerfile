FROM buildpack-deps:stretch

ENV LANG C.UTF-8

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		python3-all python3-requests python3-pip python3-setuptools python3-nose python3-coverage tox \
		debhelper dh-python devscripts build-essential fakeroot \
		file git rsync \
	&& apt-get clean

WORKDIR /tmp
ADD installPython.sh /tmp

RUN /tmp/installPython.sh 3.6.5 altinstall

RUN apt-get install -y libssl1.0-dev
RUN ./installPython.sh 3.4.8 altinstall
RUN apt-get install -y libssl-dev

RUN useradd -m -u 1000 leaf


