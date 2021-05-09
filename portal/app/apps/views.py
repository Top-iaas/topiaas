from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from flask_rq import get_queue

from app import db
from app.apps.forms import DeployNewApp
from app.decorators import admin_required
from app.email import send_email
from app.models import EditableHTML, AppInstance, User
from flask import jsonify
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
        apps_buzz.deploy_app(
            vcpu_limit, memory_limit, app_type=apps_buzz.SupportedApps.ORANGE_ML
        )
        app_instance = AppInstance(
            app_type=apps_buzz.SupportedApps.ORANGE_ML.value,
            name=form.name.data,
            url="https://google.com",
            user=current_user.id,
            vcpu_limit=form.vcpu_limit.data,
            memory_limit=form.memory_limit.data,
        )
        db.session.add(app_instance)
        db.session.commit()
        flash(
            "Instance of Orange ML is being deployed",
            "form-success",
        )
    return render_template("apps/new_app.html", form=form, app_name="Orange ML")


@apps.route("/user/<int:user_id>/delete")
@login_required
@admin_required
def delete_user_request(user_id):
    """Request deletion of a user's account."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    return render_template("admin/manage_user.html", user=user)


@apps.route("/user/<int:user_id>/_delete")
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user's account."""
    if current_user.id == user_id:
        flash(
            "You cannot delete your own account. Please ask another "
            "administrator to do this.",
            "error",
        )
    else:
        user = User.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        flash("Successfully deleted user %s." % user.full_name(), "success")
    return redirect(url_for("admin.registered_users"))


@apps.route("/supported", methods=["GET"])
@login_required
def list_supported():
    return jsonify({"SupportedApps": apps_buzz.list_supported_apps()})
