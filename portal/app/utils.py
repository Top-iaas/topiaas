from flask import url_for
from wtforms.fields import Field
from wtforms.widgets import HiddenInput
from wtforms.compat import text_type
from app.models.user import User
from minio import Minio
import os


minio_endpoint = os.environ.get("S3_ENDPOINT")
access_key = os.environ.get("S3_ACCESS_KEY")
access_secret = os.environ.get("S3_ACCESS_SECRET")
minio_cl = Minio(minio_endpoint, access_key, access_secret, secure=False)


def register_template_utils(app):
    """Register Jinja 2 helpers (called from __init__.py)."""

    @app.template_test()
    def equalto(value, other):
        return value == other

    @app.template_global()
    def is_hidden_field(field):
        from wtforms.fields import HiddenField

        return isinstance(field, HiddenField)

    app.add_template_global(index_for_role)


def index_for_role(role):
    return url_for(role.index)


class CustomSelectField(Field):
    widget = HiddenInput()

    def __init__(
        self,
        label="",
        validators=None,
        multiple=False,
        choices=[],
        allow_custom=True,
        **kwargs,
    ):
        super(CustomSelectField, self).__init__(label, validators, **kwargs)
        self.multiple = multiple
        self.choices = choices
        self.allow_custom = allow_custom

    def _value(self):
        return text_type(self.data) if self.data is not None else ""

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[1]
            self.raw_data = [valuelist[1]]
        else:
            self.data = ""


def get_user_bucket(user: User):
    return f"user.{user.id}"


def touch_bucket(bucket_name: str):
    if not minio_cl.bucket_exists(bucket_name):
        minio_cl.make_bucket(bucket_name)


def s3_upload(user: User, destination: str, file_path: str):
    bucket = get_user_bucket(user)
    touch_bucket(bucket_name=bucket)
    minio_cl.fput_object(bucket, destination, file_path)


def s3_remove(user: User, filename: str):
    bucket = get_user_bucket(user)
    minio_cl.remove_object(bucket, filename)
