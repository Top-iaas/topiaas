import random
from select import select
import string
import urllib3.exceptions
from abc import ABC, abstractmethod
from app.models.user import User
from app.lib.enumeration import SupportedApps
from app.business import k8s
from flask import abort, Response, render_template
from app.lib.enumeration import AppStatus
from app.models import AppInstance
from datetime import datetime
from app import db
from dataclasses import dataclass, field
from kubernetes.client.rest import ApiException
from typing import Dict
import logging
import yaml
import secrets


@dataclass
class AbstractApplication(ABC):
    """Class for keeping track of an item in inventory."""

    db_model: AppInstance = field(init=False)
    deployment_body: Dict = field(init=False)
    service_body: Dict = field(init=False)
    ingress_body: Dict = field(init=False)

    @abstractmethod
    def create_db_model(self):
        pass

    def deploy(self):
        validate_app_request(self.user, self.cpu_limit, self.memory_limit)
        self.app_instance = self.create_db_model()
        db.session.add(self.app_instance)
        db.session.flush()
        try:
            self.deploy_in_k8s()
        except Exception:
            db.session.delete(self.app_instance)
            raise
        db.session.commit()

    @abstractmethod
    def negotiate_k8s_resources(self):
        pass

    def render_k8s_templates(self):
        PORT = 80
        deployment_yaml = render_template(
            "k8s/app_deployment.yaml",
            name=self.model.name,
            image=self.model.image_name,
            cpu_limit=self.cpu_limit * 1000,
            memory_limit=self.memory_limit,
            port=PORT,
            password=self.password,
        )
        self.deployment_body = yaml.safe_load(deployment_yaml)
        service_yaml = render_template(
            "k8s/app_service.yaml",
            name=self.name,
            selector=self.name,
            port=PORT,
            target_port=PORT,
        )
        self.service_body = yaml.safe_load(service_yaml)
        ingress_yaml = render_template(
            "k8s/app_ingress.yaml",
            name=self.name,
            service_name=self.service_body["metadata"]["name"],
            service_port=PORT,
            path=f"/{self.name}/websockify",
        )
        self.ingress_body = yaml.safe_load(ingress_yaml)

    def deploy_in_k8s(self):
        logging.info(f"deploying app: {self.app_instance.get_k8s_name()}")
        try:
            app_url = self.negotiate_k8s_resources()
        except (ApiException, urllib3.exceptions.ProtocolError) as e:
            logging.error(e)
            remove_app(self.app_instance)
            abort(
                Response(
                    "Could not deploy application. please try again later",
                    status=503,
                )
            )
        self.app_instance.url = app_url
        self.app_instance.state = AppStatus.DEPLOYED.value
        self.app_instance.password = self.password


@dataclass
class OrangeMLApplication(AbstractApplication):
    image_name = "topiaas/orangeml:latest"

    def create_db_model(self):
        return AppInstance(
            app_type=SupportedApps.ORANGE_ML.value,
            name=self.name,
            owner=self.user.id,
            users=[self.user],
            cpu_limit=self.cpu_limit,
            memory_limit=self.memory_limit,
        )

    def negotiate_k8s_resources(self):
        return k8s.create_orangeml_instance(
            name=self.app_instance.get_k8s_name(),
            cpu_limit=self.cpu_limit,
            memory_limit=self.memory_limit,
            password=self.password,
        )


@dataclass
class InkscapeApplication(AbstractApplication):
    def create_db_model(self):
        return AppInstance(
            app_type=SupportedApps.INKSCAPE.value,
            name=self.name,
            owner=self.user.id,
            users=[self.user],
            cpu_limit=self.cpu_limit,
            memory_limit=self.memory_limit,
        )

    def negotiate_k8s_resources(self):
        return k8s.create_inkscape_instance(
            name=self.app_instance.get_k8s_name(),
            cpu_limit=self.cpu_limit,
            memory_limit=self.memory_limit,
            password=self.password,
        )


def list_supported_apps():
    return SupportedApps.values()


def validate_app_request(user, cpu_limit, memory_limit):
    consuming_apps = [app for app in user.apps if app.state == AppStatus.DEPLOYED.value]
    total_user_cpu_usage = sum((app.cpu_limit for app in consuming_apps))
    total_user_memory_usage = sum((app.memory_limit for app in consuming_apps))
    free_cpu = user.cpu_limit - total_user_cpu_usage
    free_memory = user.memory_limit - total_user_memory_usage
    if free_cpu < cpu_limit or free_memory < memory_limit:
        abort(
            Response(
                "Insufficient capacity for such application. Please review your cpu and memory limits",
                status=400,
            )
        )


def remove_app(app: AppInstance, force=False):
    if not force and app.state != AppStatus.DEPLOYED.value:
        abort(
            Response(
                "App is not in state DEPLOYED",
                status=400,
            )
        )
    name = app.get_k8s_name()
    logging.info(f"Removing app: {name}")
    try:
        k8s.delete_app_instance(name)
    except (ApiException, urllib3.exceptions.ProtocolError) as e:
        logging.error(e)
        abort(
            Response(
                "Could not delete application. please try again later",
                status=503,
            )
        )
    app.state = AppStatus.DELETED.value
    app.delete_ts = datetime.now()


def get_app_object(data: Dict) -> AbstractApplication:
    supported = {
        "orangeml": OrangeMLApplication,
        "inkscape": InkscapeApplication,
    }
    app_type = data.pop("app_type")
    if app_type not in supported:
        raise KeyError(f"type '{app_type}' not supported")
    app_class = supported[app_type]
    return app_class(**data)
