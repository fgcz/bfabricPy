ARG DEBIAN_VERSION=buster
FROM debian:${DEBIAN_VERSION}
ARG PYTHON_VERSION=3.13.0

LABEL org.opencontainers.image.authors="Leonardo Schwarz"

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y curl git bash build-essential ccache \
    && apt-get install -y libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl git libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

RUN curl https://pyenv.run | bash

ENV PATH=$PATH:/root/.pyenv/bin
RUN pyenv install $PYTHON_VERSION
RUN pyenv global $PYTHON_VERSION
ENV PATH=/root/.pyenv/versions/${PYTHON_VERSION}/bin:$PATH

RUN pip install --root-user-action ignore uv pyinstaller
RUN chmod -R 0777 /root
RUN mkdir /work && chmod 0777 /work
RUN mkdir /home/user && chmod 0777 /home/user

ENV HOME=/home/user
WORKDIR /work
