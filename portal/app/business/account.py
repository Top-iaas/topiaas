from wtforms import ValidationError
from ..models import User
from .. import db


def validate_limits(vcpu, memory):
    if vcpu == 0:
        raise ValidationError("vcpu must be >= 1")
    if memory < 512:
        raise ValidationError("memory must be >= 512")


def change_limits(user_id, vcpu=None, memory=None):
    """Change capacity limits for this user"""
    if not (vcpu or memory):
        return
    validate_limits(vcpu, memory)
    user = User.query.get_or_404(int(user_id))
    if vcpu:
        user.vcpu_limit = vcpu
    if memory:
        user.memory_limit = memory
    db.session.add(user)
    db.session.commit()
    return True
