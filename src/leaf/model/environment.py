"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import operator
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path

from leaf.core.error import InvalidSettingException
from leaf.core.settings import LeafSetting


class Environment:
    @staticmethod
    def tostring_comment(line: str):
        return "# {line}".format(line=line)

    @staticmethod
    def tostring_export(key: str, value: str):
        return 'export {key}="{value}";'.format(key=key, value=value)

    @staticmethod
    def tostring_unset(key: str):
        return "unset {key};".format(key=key)

    @staticmethod
    def build(*environments):
        out = Environment()
        for env in environments:
            if isinstance(env, Environment):
                out.append(env)
            elif isinstance(env, dict):
                out.append(Environment(content=env))
            elif env is not None:
                raise ValueError()
        return out

    def __init__(self, label: str = None, content: dict or list = None):
        self.__label = label
        self.__values = []
        self.__sub_env_list = []

        # Init content
        if isinstance(content, dict):
            for k, v in content.items():
                self.set_variable(k, v)
        elif isinstance(content, list):
            for k, v in content:
                self.set_variable(k, v)
        elif content is not None:
            raise ValueError()

    def append(self, subenv):
        if isinstance(subenv, Environment):
            self.__sub_env_list.append(subenv)
        elif subenv is not None:
            raise ValueError()

    def print_env(self, kv_consumer: callable = None, comment_consumer: callable = None):
        # Start with sub env
        for e in self.__sub_env_list:
            e.print_env(kv_consumer, comment_consumer)
        # Print self
        if len(self.__values) > 0:
            if self.__label is not None and comment_consumer is not None:
                comment_consumer(self.__label)
            if kv_consumer is not None:
                for k, v in self.__values:
                    kv_consumer(k, v)

    def tolist(self, acc=None):
        if acc is None:
            acc = []
        # Start by sub environments
        for e in self.__sub_env_list:
            e.tolist(acc=acc)
        # Add current values
        acc += self.__values
        return acc

    def keys(self):
        return set(map(operator.itemgetter(0), self.tolist()))

    def find_setting(self, setting: LeafSetting) -> str:
        out = self.find_value(setting.key)
        # Check that the value is valid
        if out is not None and not setting.is_valid(out):
            raise InvalidSettingException(setting, out)
        return out if out is not None else setting.value

    def find_value(self, key: str):
        out = None
        # First search value in sub envs
        for c in self.__sub_env_list:
            out2 = c.find_value(key)
            if out2 is not None:
                out = out2
        # Search value in self values
        for k, v in self.__values:
            if k == key:
                out = str(v)
        return out

    def is_set(self, key):
        # First search value in sub envs
        for e in self.__sub_env_list:
            if e.is_set(key):
                return True
        # Search value in self values
        for k, _ in self.__values:
            if k == key:
                return True
        return False

    def unset_variable(self, key, reccursive=True):
        self.__values = list(filter(lambda kv: kv[0] != key, self.__values))
        if reccursive:
            for c in self.__sub_env_list:
                c.unset_variable(key, reccursive=reccursive)

    def set_variable(self, key, value, replace=False, prepend=False):
        if value is None:
            raise ValueError("{key} cannot be null".format(key=key))
        if replace:
            self.unset_variable(key, reccursive=False)
        if prepend:
            self.__values.insert(0, (key, value))
        else:
            self.__values.append((key, value))

    def generate_scripts(self, activate_file: Path = None, deactivate_file: Path = None):
        """
        Generates environment script to activate and desactivate a profile
        """
        if deactivate_file is not None:
            resetmap = OrderedDict()
            for k in self.keys():
                resetmap[k] = os.environ.get(k)
            with deactivate_file.open("w") as fp:
                for k, v in resetmap.items():
                    # If the value was not present in env before, reset it
                    if v is None:
                        fp.write(Environment.tostring_unset(k) + "\n")
                    else:
                        fp.write(Environment.tostring_export(k, v) + "\n")
        if activate_file is not None:
            with activate_file.open("w") as fp:

                def comment_consumer(c):
                    fp.write(Environment.tostring_comment(c) + "\n")

                def kv_consumer(k, v):
                    fp.write(Environment.tostring_export(k, v) + "\n")

                self.print_env(kv_consumer=kv_consumer, comment_consumer=comment_consumer)


class IEnvProvider(ABC):
    def __init__(self, label):
        self.__label = label

    @abstractmethod
    def _getenvmap(self) -> dict:
        pass

    def build_environment(self) -> Environment:
        return Environment("Exported by {name}".format(name=self.__label), self._getenvmap())

    def update_environment(self, set_map: dict = None, unset_list: list = None):
        envmap = self._getenvmap()
        if set_map is not None:
            for k, v in set_map.items():
                envmap[k] = str(v)
        if unset_list is not None:
            for k in unset_list:
                if k in envmap:
                    del envmap[k]
