import subprocess
import os
import shutil
import sys
import yaml


class Installer:
    def __init__(self, workdir=f"{os.environ['HOME']}/topiaas/devenv"):
        self.WORKDIR = workdir
        self.HOST_WEBSITE_PATH = os.path.join(self.WORKDIR, "website")
        self.CONTAINER_WORKDIR = "/opt/topiaas/devenv"
        self.WEBSITE_URL = "https://github.com/MohamedKasem99/flask-base.git"
        self.CONTAINER_NAME = "topiaas_devenv"
        self.CONTAINER_IMAGE = "mohamedkasem99/topiaas_devenv"
        self.container_created = False
        if not os.path.exists(self.WORKDIR):
            os.makedirs(self.WORKDIR)

    def run_cmd(self, cmd, shell=True):
        try:
            subprocess.check_output(cmd, shell=shell)
        except subprocess.CalledProcessError as e:
            print(
                f"couldn't run command {cmd} \n stderr: {e.stderr}. \n stdout{e.stdout}"
            )
            sys.exit(1)

    def is_container_created(self):
        try:
            subprocess.check_output("docker ps | grep topiaas_devenv", shell=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def run_container_cmd(self, cmd, strict=True):
        try:
            subprocess.check_output(
                f"docker exec -ti {self.CONTAINER_NAME} bash -c '{cmd}'", shell=True
            )
            return True
        except subprocess.CalledProcessError:
            if strict:
                raise
            return False

    def clone_website_repo(self, overwrite=True):
        print("cloning website repo ...")
        if os.path.exists(self.HOST_WEBSITE_PATH):
            if overwrite:
                print(
                    "WARNING: overwriting locally exisiting website repo ...",
                    file=sys.stderr,
                )
                shutil.rmtree(self.HOST_WEBSITE_PATH)
                self.run_cmd(f"git clone {self.WEBSITE_URL} {self.HOST_WEBSITE_PATH}")
        else:
            self.run_cmd(f"git clone {self.WEBSITE_URL} {self.HOST_WEBSITE_PATH}")

    def create_container(self):
        self.run_cmd(
            f"docker run -d --hostname {self.CONTAINER_NAME} --name {self.CONTAINER_NAME} --network host --tmpfs /tmp --tmpfs /run --tmpfs /run/lock -v /sys/fs/cgroup:/sys/fs/cgroup:ro -v {self.WORKDIR}:{self.CONTAINER_WORKDIR} {self.CONTAINER_IMAGE}"
        )
        self.container_created = True

    def configure_container(self):
        self.run_container_cmd("mkdir /root/.ssh", False)
        self.run_container_cmd("mkdir /root/.kube", False)
        with open(f"{os.environ['HOME']}/.ssh/id_rsa.pub", "r") as fd:
            self.ssh_pubkey = fd.read()
        self.run_container_cmd(f'echo "{self.ssh_pubkey}" > /root/.ssh/authorized_keys')
        with open(os.path.join(os.environ["HOME"], ".kube/config")) as fd:
            kubeconfig = fd.read()
        new_kubeconfig = kubeconfig.replace(os.environ["HOME"], "/root")
        with open("/tmp/kubeconfig", "w") as fd:
            fd.write(new_kubeconfig)
        self.run_cmd("docker cp /tmp/kubeconfig topiaas_devenv:/root/.kube/config")
        self.run_cmd("docker cp ~/.minikube topiaas_devenv:/root/.minikube")

    def install_py_requirements(self):
        print("Installing devenv requirements.txt ...")
        self.run_container_cmd(
            f"pip3 install -r {self.CONTAINER_WORKDIR + '/requirements.txt'}"
        )
        print("Installing website requirements.txt ...")
        self.run_container_cmd(
            f"pip3 install -r {self.CONTAINER_WORKDIR + '/website/requirements.txt'}"
        )

    def install(self, overwrite):
        self.clone_website_repo(overwrite)
        self.run_cmd("minikube start")
        if not self.is_container_created():
            self.create_container()
        self.configure_container()
        self.install_py_requirements()


if __name__ == "__main__":
    installer = Installer()
    installer.install(False)
