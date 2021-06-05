from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField, IntegerField
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
