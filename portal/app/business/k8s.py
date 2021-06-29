import uuid
from kubernetes import client, config, watch
import time

try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

apps_v1_api = client.AppsV1Api()
core_v1_api = client.CoreV1Api()
networking_v1_beta1_api = client.NetworkingV1beta1Api()


def create_orangeml_deployment_body(name, cpu_limit, memory_limit, password):
    container = client.V1Container(
        name=name,
        image="topiaas/orangeml",
        ports=[client.V1ContainerPort(container_port=80)],
        resources=client.V1ResourceRequirements(
            limits={"cpu": f"{cpu_limit * 1000}m", "memory": f"{memory_limit}Mi"},
        ),
        env=[{"name": "PASSWORD", "value": password}],
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": name}),
        spec=client.V1PodSpec(containers=[container]),
    )

    spec = client.V1DeploymentSpec(
        replicas=1, template=template, selector={"matchLabels": {"app": name}}
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec,
    )

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


def create_service(name, app_name, port, target_port):
    body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": app_name},
        "spec": {
            "selector": {"app": app_name},
            "ports": [{"protocol": "TCP", "port": port, "targetPort": target_port}],
        },
    }
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
    body = {
        "apiVersion": "networking.k8s.io/v1beta1",
        "kind": "Ingress",
        "metadata": {
            "name": name,
            "annotations": {
                "nginx.ingress.kubernetes.io/rewrite-target": "/$1",
                "nginx.ingress.kubernetes.io/use-regex": "true",
            },
        },
        "spec": {
            "rules": [
                {
                    "host": "topiaas.ml",
                    "http": {
                        "paths": [
                            {
                                "backend": {
                                    "serviceName": service_name,
                                    "servicePort": service_port,
                                },
                                "path": path,
                                "pathType": "Prefix",
                            }
                        ]
                    },
                }
            ],
            "tls": [{"hosts": ["topiaas.ml"], "secretName": "topiaas-ml-tls"}],
        },
    }
    networking_v1_beta1_api.create_namespaced_ingress(namespace="default", body=body)


def create_orangeml_instance(name, cpu_limit, memory_limit, password):
    rand_suffix = str(uuid.uuid4()).split("-")[0]
    ingress_path = f"/{name}-{rand_suffix}/websockify"
    deployment_body = create_orangeml_deployment_body(
        name, cpu_limit, memory_limit, password
    )
    create_deployment(name=name, deployment=deployment_body)
    time.sleep(2)
    create_service(name=name, app_name=name, port=80, target_port=80)
    time.sleep(2)
    create_ingress(name=name, path=ingress_path, service_name=name, service_port=80)
    return f"topiaas.ml{ingress_path}"


def delete_app_instance(name):
    apps_v1_api.delete_namespaced_deployment(name=name, namespace="default")
    core_v1_api.delete_namespaced_service(name=name, namespace="default")
    networking_v1_beta1_api.delete_namespaced_ingress(name=name, namespace="default")
    return True
