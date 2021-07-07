from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from app.lib.enumeration import AppStatus

from .. import db

app_user_association = db.Table(
    "app_user_association",
    db.Model.metadata,
    db.Column("users_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("app_id", db.Integer, db.ForeignKey("app.id")),
)


class AppInstance(db.Model):
    __tablename__ = "app"
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.String(64))
    name = db.Column(db.String(64))
    app_type = db.Column(db.String(64))
    url = db.Column(db.String(128))
    owner = db.Column(db.Integer, db.ForeignKey("users.id"))
    users = db.relationship(
        "User", secondary=app_user_association, back_populates="apps"
    )
    vcpu_limit = db.Column(db.Integer)
    memory_limit = db.Column(db.Integer)
    password = db.Column(db.String(64), default="")
    state = Column(String(64), server_default=AppStatus.DEPLOYING.value)
    deploy_ts = Column(DateTime(), server_default=func.now())
    delete_ts = Column(DateTime())

    def __repr__(self):
        return f"<App {self.name} ID {self.id}>"

    def get_k8s_name(self):
        return f"{self.app_type}-{self.owner}-{self.id}"
