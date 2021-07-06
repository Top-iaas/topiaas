import random
import string
import subprocess
import time
from os import getenv
from os.path import basename
from tempfile import NamedTemporaryFile

import app.business.apps as apps_buzz
from app import db
from app.apps.forms import AppFileDownload, AppFileUpload, DeployNewApp
from app.business.k8s import get_orange_ml_pod_name
from app.lib.enumeration import AppStatus
from app.models import AppInstance
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, url_for
from flask.globals import request
from flask.wrappers import Response
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest

apps = Blueprint("apps", __name__)

CPU_PRICE = getenv("CPU_UNIT_PRICE", 2)
MEMORY_PRICE = getenv("MEMORY_UNIT_PRICE", 5)


@apps.route("/")
@login_required
def index():
    """User apps information page."""
    if current_user.is_admin():
        apps = list(
            AppInstance.query.filter(AppInstance.state != AppStatus.DELETED.value).all()
        )
    else:
        apps = [
            app for app in current_user.apps if app.state != AppStatus.DELETED.value
        ]
    return render_template(
        "apps/running_apps.html", apps=apps, is_admin=current_user.is_admin()
    )


@apps.route("/new/orangeml", methods=["GET", "POST"])
@login_required
def new_orangeml():
    """Create a new user."""
    form = DeployNewApp()
    if form.validate_on_submit():
        vcpu_limit, memory_limit = form.vcpu_limit.data, form.memory_limit.data
        apps_buzz.validate_app_request(current_user, vcpu_limit, memory_limit)
        password = "".join(
            random.choice(
                string.ascii_uppercase + string.ascii_lowercase + string.digits
            )
            for _ in range(8)
        )
        app_instance = AppInstance(
            app_type=apps_buzz.SupportedApps.ORANGE_ML.value,
            name=form.name.data,
            owner=current_user.id,
            users=[current_user],
            vcpu_limit=form.vcpu_limit.data,
            memory_limit=form.memory_limit.data,
            password=password,
        )
        db.session.add(app_instance)
        db.session.flush()
        app_url = apps_buzz.deploy_app(
            vcpu_limit,
            memory_limit,
            app=app_instance,
            password=password,
        )
        app_instance.url = app_url
        db.session.commit()
        flash(
            "Instance of Orange ML is being deployed",
            "form-success",
        )
    return render_template("apps/new_app.html", form=form, app_name="Orange ML")


@apps.route("/delete/<int:app_id>")
@login_required
def delete_app_instance(app_id):
    """Delete an application instance"""
    user_apps = current_user.apps
    if current_user.is_admin():
        app = AppInstance.query.filter_by(id=app_id).first_or_404()
        apps_buzz.remove_app(app)
    else:
        for app in user_apps:
            if app.id == app_id:
                apps_buzz.remove_app(app)
                flash(
                    f"Successfully deleted {app.app_type} App with id {app.id}."
                    "success",
                )
                break
        else:
            abort(403)
    db.session.commit()
    return redirect(url_for("account.index"))


@apps.route("/<int:app_id>", methods=["GET"])
@login_required
def get_app_instance(app_id):
    app = AppInstance.query.filter_by(owner=current_user.id, id=app_id).first_or_404()
    result = app.__dict__.copy()
    if result["delete_ts"]:
        result["delete_ts"] = int(result["delete_ts"].timestamp())
    result["deploy_ts"] = int(result["deploy_ts"].timestamp())
    result.pop("_sa_instance_state")
    result.pop("index")
    result["users"] = [u.id for u in app.users]
    return jsonify(result)


@apps.route("/supported", methods=["GET"])
@login_required
def list_supported():
    return jsonify({"SupportedApps": apps_buzz.list_supported_apps()})


@apps.route("/<int:app_id>/consumption", methods=["GET"])
@login_required
def get_app_usage_billing(app_id: int):
    from_ = request.args.get("from")
    if from_ is None:
        raise BadRequest("from query arg missing")
    if not from_.isnumeric():
        raise BadRequest("`from` query arg must be a valid integer")
    to = request.args.get("to")
    if to is None:
        raise BadRequest("to query arg missing")
    if not to.isnumeric():
        raise BadRequest("`to` query arg must be a valid integer")
    from_ = int(from_)
    to = int(to)

    if from_ >= to:
        raise BadRequest("`from` should be smaller than `to`")

    if from_ > time.time():
        raise BadRequest("`from` should not be greater than current time")

    app = AppInstance.query.filter_by(owner=current_user.id, id=app_id).first_or_404()

    app_from: int = int(app.deploy_ts.timestamp())
    app_to: int = int(
        app.delete_ts.timestamp()
        if app.state == AppStatus.DELETED.value
        else time.time()
    )

    left_boundary = max(app_from, from_)
    right_boundary = min(app_to, to)

    if left_boundary >= right_boundary:
        raise BadRequest("There is no consumption in the specified period")

    billing_seconds = right_boundary - left_boundary

    usage = {
        "seconds": billing_seconds,
        "from": left_boundary,
        "to": right_boundary,
        "memory_price": MEMORY_PRICE,
        "cpu_price": CPU_PRICE,
        "memory_consumption": round(
            billing_seconds / 3600 * MEMORY_PRICE * app.memory_limit, 2
        ),
        "cpu_consumption": round(
            billing_seconds / 3600 * CPU_PRICE * app.vcpu_limit, 2
        ),
    }
    return jsonify(usage)


@apps.route("/<app_instance>/download", methods=["GET", "POST"])
@login_required
def download_app_file(app_instance: str):

    form = AppFileDownload()
    if form.validate_on_submit():
        path = form.app_path.data

        pod_name = get_orange_ml_pod_name("-".join(app_instance.split("-")[:-1]))

        temp_file = NamedTemporaryFile("r+b")

        p = subprocess.run(
            ["kubectl", "cp", f"{pod_name}:{path}", f"{temp_file.name}"],
            capture_output=True,
        )
        if p.stdout:
            raise BadRequest(p.stdout.decode())

        if p.stderr:
            raise BadRequest(p.stderr.decode())

        return Response(
            temp_file,
            status=200,
            headers={
                "Content-Disposition": f"attachment; filename={basename(path)}",
            },
        )
    return render_template("apps/app_file_download.html", form=form)


@apps.route("/<app_instance>/upload", methods=["GET", "POST"])
@login_required
def upload_app_file(app_instance: str):

    form = AppFileUpload()
    if form.validate_on_submit():

        file = form.file.data
        with NamedTemporaryFile("r+b") as temp_file:

            file.save(temp_file.name)

            pod_name = get_orange_ml_pod_name("-".join(app_instance.split("-")[:-1]))

            p = subprocess.run(
                [
                    "kubectl",
                    "cp",
                    f"{temp_file.name}",
                    f"{pod_name}:{form.app_path.data}",
                ],
                capture_output=True,
            )
        if p.stdout:
            raise BadRequest(p.stdout.decode())

        if p.stderr:
            raise BadRequest(p.stderr.decode())

        return redirect(
            url_for("account.demo", app_instance_id=app_instance, host="topiaas.ml")
        )

    return render_template("apps/app_file_upload.html", form=form)
