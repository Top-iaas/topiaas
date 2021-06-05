from flask import Blueprint, flash, redirect, render_template, url_for, jsonify, abort
from flask_login import current_user, login_required

from app import db
from app.apps.forms import DeployNewApp
from app.models import AppInstance, User
import app.business.apps as apps_buzz

apps = Blueprint("apps", __name__)


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
        app_instance = AppInstance(
            app_type=apps_buzz.SupportedApps.ORANGE_ML.value,
            name=form.name.data,
            owner=current_user.id,
            users=[current_user],
            vcpu_limit=form.vcpu_limit.data,
            memory_limit=form.memory_limit.data,
        )
        db.session.add(app_instance)
        db.session.flush()
        app_url = apps_buzz.deploy_app(
            vcpu_limit,
            memory_limit,
            app_type=apps_buzz.SupportedApps.ORANGE_ML,
            app_id=app_instance.id,
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
            user_apps.remove(app)
            db.session.delete(app)
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
    result.pop("_sa_instance_state")
    result.pop("index")
    result["users"] = [u.id for u in app.users]
    return jsonify(result)


@apps.route("/supported", methods=["GET"])
@login_required
def list_supported():
    return jsonify({"SupportedApps": apps_buzz.list_supported_apps()})
