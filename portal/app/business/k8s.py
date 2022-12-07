import time
import uuid
import yaml

from kubernetes import client, config
from typing import Callable
from flask import render_template

from kubernetes.client.rest import ApiException

try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

apps_v1_api = client.AppsV1Api()
core_v1_api = client.CoreV1Api()
networking_v1_beta1_api = client.NetworkingV1beta1Api()


def create_orangeml_deployment_body(name, cpu_limit, memory_limit, password):
    deployment_yaml = render_template(
        "k8s/app_deployment.yaml",
        name=name,
        image="topiaas/orangeml:latest",
        cpu_limit=cpu_limit * 1000,
        memory_limit=memory_limit,
        port=80,
        password=password,
    )
    deployment = yaml.safe_load(deployment_yaml)

    return deployment


def create_inkscape_deployment_body(name, cpu_limit, memory_limit, password):
    deployment_yaml = render_template(
        "k8s/app_deployment.yaml",
        name=name,
        image="topiaas/inkscape:latest",
        cpu_limit=cpu_limit * 1000,
        memory_limit=memory_limit,
        port=80,
        password=password,
    )
    deployment = yaml.safe_load(deployment_yaml)

    return deployment


def create_deployment(name, deployment):
    resp = apps_v1_api.create_namespaced_deployment(
        body=deployment, namespace="default"
    )

    print(f"\n[INFO] deployment `{name}` created.\n")
    print("%s\t%s\t\t\t%s\t%s" % ("NAMESPACE", "NAME", "REVISION", "IMAGE"))
    print(
        "%s\t\t%s\t%s\t\t%s\n"
        % (
            resp.metadata.namespace,
            resp.metadata.name,
            resp.metadata.generation,
            resp.spec.template.spec.containers[0].image,
        )
    )


def create_service(name, port, target_port):
    body_yaml = render_template(
        "k8s/app_service.yaml", name=name, port=port, target_port=target_port
    )
    body = yaml.safe_load(body_yaml)

    resp = core_v1_api.create_namespaced_service(body=body, namespace="default")

    print(f"\n[INFO] Service `{name}` created.\n")
    print("%s\t%s\t\t" % ("NAMESPACE", "NAME"))
    print(
        "%s\t\t%s\t\n"
        % (
            resp.metadata.namespace,
            resp.metadata.name,
        )
    )


def create_ingress(name, path, service_name, service_port):
    body_yaml = render_template(
        "k8s/app_ingress.yaml",
        name=name,
        service_name=service_name,
        service_port=service_port,
        path=path,
    )
    body = yaml.safe_load(body_yaml)
    networking_v1_beta1_api.create_namespaced_ingress(namespace="default", body=body)


def create_instance(deployment_body, name):
    rand_suffix = str(uuid.uuid4()).split("-")[0]
    ingress_path = f"/{name}-{rand_suffix}/websockify"
    create_deployment(name=name, deployment=deployment_body)
    time.sleep(2)
    create_service(name=name, port=80, target_port=80)
    time.sleep(2)
    create_ingress(name=name, path=ingress_path, service_name=name, service_port=80)
    return f"topiaas.ml{ingress_path}"


def create_orangeml_instance(name, cpu_limit, memory_limit, password):
    rand_suffix = str(uuid.uuid4()).split("-")[0]
    ingress_path = f"/{name}-{rand_suffix}/websockify"
    deployment_body = create_orangeml_deployment_body(
        name, cpu_limit, memory_limit, password
    )
    create_deployment(name=name, deployment=deployment_body)
    time.sleep(2)
    create_service(name=name, port=80, target_port=80)
    time.sleep(2)
    create_ingress(name=name, path=ingress_path, service_name=name, service_port=80)
    return f"topiaas.ml{ingress_path}"


def create_inkscape_instance(name, cpu_limit, memory_limit, password):
    rand_suffix = str(uuid.uuid4()).split("-")[0]
    ingress_path = f"/{name}-{rand_suffix}/websockify"
    deployment_body = create_inkscape_deployment_body(
        name, cpu_limit, memory_limit, password
    )
    create_deployment(name=name, deployment=deployment_body)
    time.sleep(2)
    create_service(name=name, port=80, target_port=80)
    time.sleep(2)
    create_ingress(name=name, path=ingress_path, service_name=name, service_port=80)
    return f"topiaas.ml{ingress_path}"


def k8s_delete_if_exists(call: Callable, name: str, namespace: str = "default"):
    try:
        call(name=name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            raise


def delete_app_instance(name):
    k8s_delete_if_exists(
        apps_v1_api.delete_namespaced_deployment, name=name, namespace="default"
    )
    k8s_delete_if_exists(
        core_v1_api.delete_namespaced_service, name=name, namespace="default"
    )
    k8s_delete_if_exists(
        networking_v1_beta1_api.delete_namespaced_ingress,
        name=name,
        namespace="default",
    )
    return True


def list_deployment_pods(deployment_name: str):
    return core_v1_api.list_namespaced_pod(
        "default", label_selector=f"app={deployment_name}"
    )


def get_orange_ml_pod_name(app_name: str):
    return list_deployment_pods(app_name).items[0].metadata.name
