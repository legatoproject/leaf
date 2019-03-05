"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
import re


class DefaultValidator:
    def __call__(self, v):
        return True


class EnumValidator:
    def __init__(self, values):
        self.__values = set(values)

    def __call__(self, value):
        return value in self.__values


class RegexValidator:
    def __init__(self, pattern):
        self.__pattern = pattern

    def __call__(self, value):
        return re.fullmatch(self.__pattern, value) is not None


class Setting:

    __FALSE_VALUES = ("", "0", "false", "no")

    def __init__(self, key: str, default: str = None, validator: callable = None):
        self.__key = key
        self.__validator = validator or DefaultValidator()
        self.__default = default
        if default is not None and not self.is_valid(default):
            raise ValueError("Invalid default value {0}".format(default))

    @property
    def key(self):
        return self.__key

    @property
    def default(self):
        return self.__default

    @property
    def value(self):
        if self.is_set():
            v = os.getenv(self.key)
            if self.is_valid(v):
                return v
        return self.default

    @value.setter
    def value(self, newvalue: str):
        if newvalue is None:
            if self.key in os.environ:
                del os.environ[self.key]
        else:
            newvalue = str(newvalue)
            if not self.is_valid(newvalue):
                raise ValueError("Invalid value: {0}".format(newvalue))
            os.environ[self.key] = newvalue

    def is_set(self):
        return self.key in os.environ

    def is_valid(self, value: str):
        return self.__validator(value)

    def as_boolean(self):
        v = self.value
        return v is not None and v.strip().lower() not in Setting.__FALSE_VALUES

    def as_int(self, default: int = None):
        v = self.value
        return default if v is None else int(v)

    def __str__(self):
        v = self.value
        if v is None:
            return ""
        return self.value


class StaticSettings:
    @classmethod
    def values(cls):
        return [s for s in cls.__dict__.values() if isinstance(s, Setting)]

    @classmethod
    def get_by_key(cls, key):
        for s in cls.values():
            if s.key == key:
                return s
