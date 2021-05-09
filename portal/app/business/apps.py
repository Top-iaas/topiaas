from app.lib.enumeration import SupportedApps
from flask import abort, Response


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


def deploy_app(vcpu_limit, memory_limit, app_type):
    pass
