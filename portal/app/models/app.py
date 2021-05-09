from .. import db


class AppInstance(db.Model):
    __tablename__ = "app"
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.String(64))
    name = db.Column(db.String(64))
    app_type = db.Column(db.String(64))
    url = db.Column(db.String(128))
    user = db.Column(db.Integer, db.ForeignKey("users.id"))
    vcpu_limit = db.Column(db.Integer)
    memory_limit = db.Column(db.Integer)

    def __repr__(self):
        return "<App '%s' ID '%d'>" % self.name, self.id
