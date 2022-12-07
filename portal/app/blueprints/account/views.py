from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    abort,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_rq import get_queue

from app import db
from app.blueprints.account.forms import (
    ChangeEmailForm,
    ChangePasswordForm,
    CreatePasswordForm,
    LoginForm,
    RegistrationForm,
    RequestResetPasswordForm,
    ResetPasswordForm,
    ChangeCapacityLimits,
)
from app.blueprints.apps.forms import S3FileUpload
from app.lib.utils import s3_upload, s3_remove
from app.lib.email import send_email
from app.models import User
from app.models.app import AppFile
from app.business import account as account_buzz
from werkzeug.utils import secure_filename
from werkzeug import Response
from minio.error import MinioException, S3Error, ServerError
from app.lib.utils import is_safe_url
import os

account = Blueprint("account", __name__)


@account.route("/login", methods=["GET", "POST"])
def login():
    """Log in an existing user."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if (
            user is not None
            and user.password_hash is not None
            and user.verify_password(form.password.data)
        ):
            login_user(user, form.remember_me.data)
            flash("You are now logged in. Welcome back!", "success")
            # check against open redirects
            _next = request.args.get("next")
            if _next and is_safe_url(_next):
                return redirect(_next)
            return redirect(url_for("main.index"))
        else:
            flash("Invalid email or password.", "error")
    return render_template("account/login.html", form=form)


@account.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user, and send them a confirmation email."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data,
            cpu_limit=form.cpu_limit.data,
            memory_limit=form.memory_limit.data,
        )
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        confirm_link = url_for("account.confirm", token=token, _external=True)
        get_queue().enqueue(
            send_email,
            recipient=user.email,
            subject="Confirm Your Account",
            template="account/email/confirm",
            user=user,
            confirm_link=confirm_link,
        )
        flash("A confirmation link has been sent to {}.".format(user.email), "warning")
        return redirect(url_for("main.index"))
    return render_template("account/register.html", form=form)


@account.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@account.route("/manage", methods=["GET", "POST"])
@account.route("/manage/info", methods=["GET", "POST"])
@login_required
def manage():
    """Display a user's account information."""
    return render_template("account/manage.html", user=current_user, form=None)


@account.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    """Respond to existing user's request to reset their password."""
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            reset_link = url_for("account.reset_password", token=token, _external=True)
            get_queue().enqueue(
                send_email,
                recipient=user.email,
                subject="Reset Your Password",
                template="account/email/reset_password",
                user=user,
                reset_link=reset_link,
                next=request.args.get("next"),
            )
        flash(
            "A password reset link has been sent to {}.".format(form.email.data),
            "warning",
        )
        return redirect(url_for("account.login"))
    return render_template("account/reset_password.html", form=form)


@account.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset an existing user's password."""
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash("Invalid email address.", "form-error")
            return redirect(url_for("main.index"))
        if user.reset_password(token, form.new_password.data):
            flash("Your password has been updated.", "form-success")
            return redirect(url_for("account.login"))
        else:
            flash("The password reset link is invalid or has expired.", "form-error")
            return redirect(url_for("main.index"))
    return render_template("account/reset_password.html", form=form)


@account.route("/manage/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change an existing user's password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            db.session.commit()
            flash("Your password has been updated.", "form-success")
            return redirect(url_for("main.index"))
        else:
            flash("Original password is invalid.", "form-error")
    return render_template("account/manage.html", form=form)


@account.route("/manage/change-email", methods=["GET", "POST"])
@login_required
def change_email_request():
    """Respond to existing user's request to change their email."""
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            change_email_link = url_for(
                "account.change_email", token=token, _external=True
            )
            user = current_user._get_current_object()
            get_queue().enqueue(
                send_email,
                recipient=new_email,
                subject="Confirm Your New Email",
                template="account/email/change_email",
                # current_user is a LocalProxy, we want the underlying user
                # object
                user=user,
                change_email_link=change_email_link,
            )
            flash(
                "A confirmation link has been sent to {}.".format(new_email), "warning"
            )
            return redirect(url_for("main.index"))
        else:
            flash("Invalid email or password.", "form-error")
    return render_template("account/manage.html", form=form)


@account.route("/manage/change-capacity-limits", methods=["GET", "POST"])
@login_required
def change_capacity_limits():
    """Change an existing user's capacity limits."""
    form = ChangeCapacityLimits()
    if form.validate_on_submit():
        account_buzz.change_limits(
            current_user.id, form.cpu_limit.data, form.memory_limit.data
        )
        flash("Capacity limits have been set successfully", "form-success")
        return redirect(url_for("main.index"))
    return render_template("account/manage.html", form=form)


@account.route("/manage/change-email/<token>", methods=["GET", "POST"])
@login_required
def change_email(token):
    """Change existing user's email with provided token."""
    if current_user.change_email(token):
        flash("Your email address has been updated.", "success")
    else:
        flash("The confirmation link is invalid or has expired.", "error")
    return redirect(url_for("main.index"))


@account.route("/confirm-account")
@login_required
def confirm_request():
    """Respond to new user's request to confirm their account."""
    token = current_user.generate_confirmation_token()
    confirm_link = url_for("account.confirm", token=token, _external=True)
    user = current_user._get_current_object()
    get_queue().enqueue(
        send_email,
        recipient=current_user.email,
        subject="Confirm Your Account",
        template="account/email/confirm",
        # current_user is a LocalProxy, we want the underlying user object
        user=user,
        confirm_link=confirm_link,
    )
    flash(
        "A new confirmation link has been sent to {}.".format(current_user.email),
        "warning",
    )
    return redirect(url_for("main.index"))


@account.route("/confirm-account/<token>")
@login_required
def confirm(token):
    """Confirm new user's account with provided token."""
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    if current_user.confirm_account(token):
        flash("Your account has been confirmed.", "success")
    else:
        flash("The confirmation link is invalid or has expired.", "error")
    return redirect(url_for("main.index"))


@account.route("/join-from-invite/<int:user_id>/<token>", methods=["GET", "POST"])
def join_from_invite(user_id, token):
    """
    Confirm new user's account with provided token and prompt them to set
    a password.
    """
    if current_user is not None and current_user.is_authenticated:
        flash("You are already logged in.", "error")
        return redirect(url_for("main.index"))

    new_user = User.query.get(user_id)
    if new_user is None:
        return redirect(404)

    if new_user.password_hash is not None:
        flash("You have already joined.", "error")
        return redirect(url_for("main.index"))

    if new_user.confirm_account(token):
        form = CreatePasswordForm()
        if form.validate_on_submit():
            new_user.password = form.password.data
            db.session.add(new_user)
            db.session.commit()
            flash(
                "Your password has been set. After you log in, you can "
                'go to the "Your Account" page to review your account '
                "information and settings.",
                "success",
            )
            return redirect(url_for("account.login"))
        return render_template("account/join_invite.html", form=form)
    else:
        flash(
            "The confirmation link is invalid or has expired. Another "
            "invite email with a new link has been sent to you.",
            "error",
        )
        token = new_user.generate_confirmation_token()
        invite_link = url_for(
            "account.join_from_invite", user_id=user_id, token=token, _external=True
        )
        get_queue().enqueue(
            send_email,
            recipient=new_user.email,
            subject="You Are Invited To Join",
            template="account/email/invite",
            user=new_user,
            invite_link=invite_link,
        )
    return redirect(url_for("main.index"))


@account.before_app_request
def before_request():
    """Force user to confirm email before accessing login-required routes."""
    if (
        current_user.is_authenticated
        and not current_user.confirmed
        and request.endpoint[:8] != "account."
        and request.endpoint != "static"
    ):
        return redirect(url_for("account.unconfirmed"))


@account.route("/unconfirmed")
def unconfirmed():
    """Catch users with unconfirmed emails."""
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for("main.index"))
    return render_template("account/unconfirmed.html")


@account.route("/", methods=["GET", "POST"])
@login_required
def index():
    """User dashboard page."""
    return render_template("account/index.html", apps=current_user.apps)


@account.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    """User billing page."""
    return render_template("account/billing.html", apps=current_user.apps)


@account.route("<host>/<app_instance_id>/websockify", methods=["GET", "POST"])
@login_required
def demo(host, app_instance_id):
    """Instance of orangeML"""
    return render_template("account/app_ui.html", app_instance=app_instance_id)


@account.route("/uploadFileToS3", methods=["GET", "POST"])
def upload_file_to_s3():
    form = S3FileUpload()
    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        file_path = os.path.join("/tmp", filename)
        f.save(file_path)
        try:
            s3_upload(current_user, filename, file_path)
            _file = AppFile(name=filename, user=current_user)
            db.session.add(_file)
            db.session.commit()
        except (MinioException, S3Error, ServerError):
            abort(
                Response(
                    "Error while uploading the file to remote storage",
                    status=503,
                )
            )
        finally:
            os.remove(file_path)
        return redirect(url_for("account.storage_files"))
    return render_template("account/upload_file.html", form=form)


@account.route("/removeStorageFile/<string:filename>", methods=["GET", "POST"])
def remove_file_in_s3(filename):
    """Delete a file from the S3 storage"""
    if not AppFile.query.filter_by(user=current_user, name=filename):
        abort(
            Response(
                f"can not find file with name {filename}",
                status=404,
            )
        )
    try:
        s3_remove(current_user, filename)
    except (MinioException, S3Error, ServerError):
        abort(
            Response(
                "Could not remove file from remote storage",
                status=503,
            )
        )
    file = AppFile.query.filter_by(name=filename).first_or_404()
    db.session.delete(file)
    db.session.commit()
    return redirect(url_for("account.storage_files"))


@account.route("/storageFiles", methods=["GET", "POST"])
@login_required
def storage_files():
    return render_template(
        "account/storage_files.html", storage_files=current_user.files
    )
