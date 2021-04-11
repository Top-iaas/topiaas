# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.163.1/containers/ubuntu/.devcontainer/base.Dockerfile

FROM mcr.microsoft.com/vscode/devcontainers/python:3

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y vim ipython3 python3-pip git openssh-server openssh-client net-tools wget curl build-essential libpq-dev
ADD portal/requirements.txt /opt/topiaas/requirements.txt
RUN pip3 install flake8==3.9.0 black==20.8b1
RUN pip3 install -r /opt/topiaas/requirements.txt
# install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
