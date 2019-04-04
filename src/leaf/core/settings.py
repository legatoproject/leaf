"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import operator
import os
import re
from pathlib import Path

_FALSE_VALUES = ("", "0", "false", "no")


class DefaultValidator:
    def __call__(self, v):
        return True

    def __str__(self):
        return ""


class RegexValidator:
    def __init__(self, pattern):
        if not isinstance(pattern, str):
            raise ValueError()
        self.__pattern = pattern

    def __call__(self, value):
        return re.fullmatch(self.__pattern, value) is not None

    def __str__(self):
        return self.__pattern


class EnvVar:
    def __init__(self, key: str, default=None, validator: callable = None):
        self.__key = key
        self.__default = None if default is None else str(default)
        self.__validator = validator or DefaultValidator()

        # Check default value is valid
        if self.default is not None and not self.is_valid(self.default):
            raise ValueError("Invalid default value {0}".format(self.default))

        # Set the default valud in env if unset of invalid
        if not self.is_set():
            self.value = self.default

    @property
    def key(self):
        return self.__key

    @property
    def is_valid(self):
        return self.__validator

    @property
    def default(self):
        return self.__default

    @property
    def value(self):
        if self.is_set():
            return os.getenv(self.key)
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
        return self.key in os.environ and self.is_valid(os.getenv(self.key))

    def as_boolean(self):
        v = self.value
        return v is not None and v.strip().lower() not in _FALSE_VALUES

    def as_path(self):
        return Path(os.path.expanduser(self.value))

    def as_int(self, default: int = None):
        v = self.value
        return default if v is None else int(v)

    def __str__(self):
        v = self.value
        if v is None:
            return ""
        return self.value


class LeafSetting(EnvVar):
    def __init__(self, identifier: str, key: str, description: str = None, default: str = None, validator: callable = None):
        EnvVar.__init__(self, key, default=default, validator=validator)
        self.__identifier = identifier
        self.__description = description

    @property
    def identifier(self):
        return self.__identifier

    @property
    def description(self):
        return self.__description


class StaticSettings:
    @classmethod
    def values(cls):
        # Since Python 3.4 and 3.5 do not sort keys by declaration order in class dict, sort keys by attribute name in class
        return [e for _, e in sorted(cls.__dict__.items(), key=operator.itemgetter(0)) if isinstance(e, EnvVar)]

    @classmethod
    def get_by_key(cls, key):
        for s in cls.values():
            if s.key == key:
                return s
