from app.lib.enumeration import SupportedApps
from app.business import k8s
from flask import abort, Response
from flask_login import current_user


def list_supported_apps():
    return SupportedApps.values()


def validate_app_request(user, vcpu_limit, memory_limit):
    total_user_cpu_usage = sum((app.vcpu_limit for app in user.apps))
    total_user_memory_usage = sum((app.memory_limit for app in user.apps))
    free_cpu = user.vcpu_limit - total_user_cpu_usage
    free_memory = user.memory_limit - total_user_memory_usage
    if free_cpu < vcpu_limit or free_memory < memory_limit:
        abort(
            Response(
                "Insufficient capacity for such application. Please review your cpu and memory limits",
                status=400,
            )
        )


def _get_app_name(app_type, app_id):
    return f"{app_type}-{current_user.id}-{app_id}"


def deploy_app(vcpu_limit, memory_limit, app_type, app_id):
    name = _get_app_name(app_type, app_id)
    if app_type == SupportedApps.ORANGE_ML:
        return k8s.create_orangeml_instance(
            name=name, cpu_limit=vcpu_limit, memory_limit=memory_limit
        )


def remove_app(app_type, app_id):
    name = _get_app_name(app_type, app_id)
    return k8s.delete_app_instance(name)
