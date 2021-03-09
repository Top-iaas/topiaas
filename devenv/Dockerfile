FROM jrei/systemd-ubuntu:20.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y vim ipython3 python3-pip mongodb redis git openssh-server openssh-client net-tools wget curl build-essential libpq-dev

# install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
