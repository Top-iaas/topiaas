from enum import Enum
from enum import IntEnum as _IntEnum


class StringEnum(Enum):
    def __eq__(self, value):
        if isinstance(value, str):
            return self.value == value
        if isinstance(value, StringEnum):
            return self.value == value.value
        return self.value == str(value)

    def __hash__(self):
        return self.value.__hash__()

    def __str__(self):
        return self.value

    def __repr__(self):
        return self._name_

    @classmethod
    def values(cls):
        return list(val.value for val in cls)

    @classmethod
    def from_string(cls, value):
        for enum in cls:
            if enum.value == value:
                return enum
        raise KeyError("%s does not contain an enum with value %s" % (cls, value))

    @classmethod
    def get_by_name(cls, name):
        try:
            return getattr(cls, name)
        except AttributeError:
            raise KeyError("%s does not contain an enum with name %s" % (cls, name))


class IntEnum(_IntEnum):
    def __eq__(self, value):
        if isinstance(value, int):
            return self.value == value
        if isinstance(value, IntEnum):
            return self.value == value.value
        return self.value == int(value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self._name_

    @classmethod
    def values(cls):
        return list(val.value for val in cls)


class SupportedApps(StringEnum):
    ORANGE_ML = "orangeml"


class AppStatus(StringEnum):
    DEPLOYED = "deployed"
    DELETED = "deleted"
