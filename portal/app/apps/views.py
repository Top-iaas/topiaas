import random
import string
from datetime import datetime
from os import getenv
from time import time

import app.business.apps as apps_buzz
from app import db
from app.apps.forms import DeployNewApp
from app.lib.enumeration import AppStatus
from app.models import AppInstance, User
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, url_for
from flask.globals import request
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest

apps = Blueprint("apps", __name__)

CPU_PRICE = getenv("CPU_UNIT_PRICE", 2)
MEMORY_PRICE = getenv("MEMORY_UNIT_PRICE", 5)


@apps.route("/")
@login_required
def index():
    """User apps information page."""
    return render_template("apps/running_apps.html", apps=current_user.apps)


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
            app_type=apps_buzz.SupportedApps.ORANGE_ML,
            app_id=app_instance.id,
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
    user_apps = User.query.filter_by(id=current_user.id).first_or_404().apps
    for app in user_apps:
        if app.id == app_id:
            apps_buzz.remove_app(app_type=app.app_type, app_id=app.id)
            app.state = AppStatus.DELETED.value
            app.delete_ts = datetime.now()
            db.session.commit()
            flash(
                f"Successfully deleted {app.app_type} App with id {app.id}." "success",
            )
            break
    else:
        abort(403)
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

    if from_ > time():
        raise BadRequest("`from` should not be greater than current time")

    app = AppInstance.query.filter_by(owner=current_user.id, id=app_id).first_or_404()

    app_from: int = int(app.deploy_ts.timestamp())
    app_to: int = int(
        app.delete_ts.timestamp() if app.state == AppStatus.DELETED.value else time()
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
