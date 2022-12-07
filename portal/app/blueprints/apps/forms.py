from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms.fields import IntegerField, StringField, SubmitField
from wtforms.validators import InputRequired, NumberRange
from flask_wtf.file import FileField, FileRequired


class DeployNewApp(FlaskForm):
    app_type = StringField(
        "Type",
        validators=[InputRequired()],
    )
    name = StringField(
        "Name",
        validators=[InputRequired()],
    )
    cpu_limit = IntegerField(
        "CPU capacity",
        validators=[InputRequired(), NumberRange(min=1)],
    )
    memory_limit = IntegerField(
        "memory Capacity", validators=[InputRequired(), NumberRange(min=512)]
    )
    submit = SubmitField("Deploy")


class AppFileUpload(FlaskForm):
    app_path = StringField(
        "App path to save file at",
        description="absolute path (e. g. home/<filename> )",
        validators=[InputRequired()],
    )
    file = FileField("Upload File", validators=[FileRequired()])
    submit = SubmitField("Upload")


class APPS3FileUpload(FlaskForm):
    app_path = StringField(
        "App path to save file at",
        description="absolute path (e. g. home/<filename> )",
        validators=[InputRequired()],
    )
    storage_file = StringField("Name of file in storage", validators=[InputRequired()])
    submit = SubmitField("Upload")


class AppFileDownload(FlaskForm):
    app_path = StringField(
        "App path to get file from",
        description="absolute path (e. g. home/<filename> )",
        validators=[InputRequired()],
    )
    submit = SubmitField("Download")


class S3FileUpload(FlaskForm):
    file = FileField(
        "Upload File",
        description="absolute path (e. g. home/<filename> )",
        validators=[FileRequired()],
    )
    submit = SubmitField("Upload")
    # app_path = StringField("Path in App instance", validators=[InputRequired()])
