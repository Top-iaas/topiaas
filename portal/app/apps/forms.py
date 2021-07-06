from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms.fields import IntegerField, StringField, SubmitField
from wtforms.validators import InputRequired, NumberRange


class DeployNewApp(FlaskForm):
    name = StringField(
        "Name",
        validators=[InputRequired()],
    )
    vcpu_limit = IntegerField(
        "CPU capacity",
        validators=[InputRequired(), NumberRange(min=1)],
    )
    memory_limit = IntegerField(
        "memory Capacity", validators=[InputRequired(), NumberRange(min=512)]
    )
    submit = SubmitField("Deploy")


class AppFileUpload(FlaskForm):
    app_path = StringField("App path to save file at", validators=[InputRequired()])
    file = FileField("Upload File", validators=[FileRequired()])
    submit = SubmitField("Upload")


class AppFileDownload(FlaskForm):
    app_path = StringField("App path to get file from", validators=[InputRequired()])
    submit = SubmitField("Download")
