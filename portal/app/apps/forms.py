from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField, IntegerField
from wtforms.validators import InputRequired, NumberRange
from flask_wtf.file import FileField, FileRequired


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


class S3FileUpload(FlaskForm):
    file = FileField("Upload File", validators=[FileRequired()])
    submit = SubmitField("Upload")
    # app_path = StringField("Path in App instance", validators=[InputRequired()])
