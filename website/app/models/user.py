from flask import current_app
from flask_login import AnonymousUserMixin, UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from .. import db, login_manager


class Permission:
    GENERAL = 0x01
    ADMINISTER = 0xFF


class Role(db.Document):
    name = db.StringField(primary_key=True)
    index = db.StringField()
    default = db.BooleanField(default=False, index=True)
    permissions = db.IntField()
    users = db.ListField(db.ObjectIdField, default=[])

    @classmethod
    def insert_roles(cls):
        roles = {
            "User": (Permission.GENERAL, "main", True),
            "Administrator": (
                Permission.ADMINISTER,  # grants all permissions
                "admin",
                False,
            ),
        }
        for r in roles:
            role = cls.objects(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.index = roles[r][1]
            role.default = roles[r][2]
            role.save()

    @classmethod
    def list(cls, **filter_kwargs) -> db.QuerySet:
        return cls.objects().filter(**filter_kwargs)

    @classmethod
    def get_by_name(cls, name) -> "Role":
        return cls.objects(name=name).first_or_404()

    def __repr__(self):
        return "<Role '%s'>" % self.name


class User(UserMixin, db.Document):
    confirmed = db.BooleanField(default=False)
    first_name = db.StringField(required=True)
    last_name = db.StringField(required=True)
    email = db.StringField(primary_key=True, required=True)
    password_hash = db.StringField(required=True)
    role_id = db.StringField()

    def __init__(self, **kwargs):
        password = kwargs.pop("password", None)
        super(User, self).__init__(**kwargs)
        if self.role_id is None:
            if self.email == current_app.config["ADMIN_EMAIL"]:
                admin_role = Role.list(permissions=Permission.ADMINISTER).first()
                if admin_role:
                    self.role_id = admin_role.name
            if self.role_id is None:
                self.role_id = Role.list(default=True).first().name
        if password:
            self.password = password

    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def can(self, permissions):
        return (
            self.role_id is not None
            and (Role.get_by_name(self.role_id).permissions & permissions)
            == permissions
        )

    def is_admin(self):
        return self.can(Permission.ADMINISTER)

    def get_id(self):
        return self.email

    @property
    def role(self):
        return Role.get_by_name(self.role_id)

    @property
    def password(self):
        raise AttributeError("`password` is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=604800):
        """Generate a confirmation token to email a new user."""

        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"confirm": self.id})

    def generate_email_change_token(self, new_email, expiration=3600):
        """Generate an email change token to email an existing user."""
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"change_email": self.id, "new_email": new_email})

    def generate_password_reset_token(self, expiration=3600):
        """
        Generate a password reset change token to email to an existing user.
        """
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"reset": self.id})

    def confirm_account(self, token):
        """Verify that the provided token is for this user's id."""
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get("confirm") != self.id:
            return False
        self.confirmed = True
        self.save()
        return True

    def change_email(self, token):
        """Verify the new email for this user."""
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get("change_email") != self.id:
            return False
        new_email = data.get("new_email")
        if new_email is None:
            return False
        if self.list(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.save()
        return True

    def reset_password(self, token, new_password):
        """Verify the new password for this user."""
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get("reset") != self.id:
            return False
        self.password = new_password
        self.save()
        return True

    @staticmethod
    def generate_fake(count=100, **kwargs):
        """Generate a number of fake users for testing."""
        from random import seed, choice
        from faker import Faker

        fake = Faker()
        roles = Role.objects().all()

        seed()
        for i in range(count):
            u = User(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                password="password",
                confirmed=True,
                role_id=choice(roles).name,
                **kwargs
            )
            u.save()

    def __repr__(self):
        return "<User '%s'>" % self.full_name()

    @classmethod
    def list(cls, **filter_kwargs) -> list:
        return cls.objects().filter(**filter_kwargs)


class AnonymousUser(AnonymousUserMixin):
    def can(self, _):
        return False

    def is_admin(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.objects(email=user_id).first()
