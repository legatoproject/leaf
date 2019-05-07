"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path

from leaf.core import REFERENCE_ENVIRON
from leaf.core.error import InvalidSettingException
from leaf.core.settings import LeafSetting


class Environment:
    @staticmethod
    def tostring_comment(line: str):
        return "# {line}".format(line=line)

    @staticmethod
    def tostring_export(key: str, value: str):
        if value is None:
            return Environment.tostring_unset(key)
        return 'export {key}="{value}";'.format(key=key, value=value)

    @staticmethod
    def tostring_unset(key: str):
        return "unset {key};".format(key=key)

    @staticmethod
    def tostring_file(file: str or Path):
        return 'test -r "{0}" && source "{0}";'.format(file)

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

    def __init__(self, label: str = None, content: dict or list = None, in_files: list = None, out_files: list = None):
        self.__label = label
        self.__values = []
        self.__in_files = in_files
        self.__out_files = out_files
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

    def activate(self, comment_consumer: callable = None, kv_consumer: callable = None, file_consumer: callable = None):
        # Start with sub env
        for e in self.__sub_env_list:
            e.activate(comment_consumer=comment_consumer, kv_consumer=kv_consumer, file_consumer=file_consumer)
        # Activate self
        if len(self.__values) > 0 or len(self.__values) > 0 or len(self.__values) > 0:
            if self.__label and comment_consumer:
                comment_consumer(self.__label)
            if kv_consumer:
                for k, v in self.__values:
                    kv_consumer(k, v)
            if file_consumer and self.__in_files:
                for f in self.__in_files:
                    file_consumer(f)

    def deactivate(self, comment_consumer: callable = None, kv_consumer: callable = None, file_consumer: callable = None):
        # Start with sub env
        for e in self.__sub_env_list:
            e.deactivate(comment_consumer=comment_consumer, kv_consumer=kv_consumer, file_consumer=file_consumer)
        # Deactivate self
        if len(self.__values) > 0 or len(self.__values) > 0 or len(self.__values) > 0:
            if self.__label and comment_consumer:
                comment_consumer(self.__label)
            if file_consumer and self.__out_files:
                for f in self.__out_files:
                    file_consumer(f)
            if kv_consumer:
                for k, _ in self.__values:
                    kv_consumer(k, REFERENCE_ENVIRON.get(k))

    def print_env(self, kv_consumer: callable = None, comment_consumer: callable = None):
        # Start with sub env
        for e in self.__sub_env_list:
            e.print_env(kv_consumer, comment_consumer)
        # Print self
        if len(self.__values) > 0 or len(self.__values) > 0 or len(self.__values) > 0:
            if self.__label is not None and comment_consumer is not None:
                comment_consumer(self.__label)
            if kv_consumer is not None:
                for k, v in self.__values:
                    kv_consumer(k, v)

    def find_setting(self, setting: LeafSetting) -> str:
        out = self.find_value(setting.key)
        # Check that the value is valid
        if out is not None and not setting.is_valid(out):
            raise InvalidSettingException(setting, out)
        return out if out is not None else setting.value

    def find_value(self, key: str):
        def visitor(k, v):
            if k == key:
                values.append(v)

        values = []
        self.activate(kv_consumer=visitor)
        return values[-1] if len(values) > 0 else None

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
        if activate_file is not None:
            with activate_file.open("w") as fp:
                self.activate(
                    comment_consumer=lambda c: fp.write(Environment.tostring_comment(c) + "\n"),
                    kv_consumer=lambda k, v: fp.write(Environment.tostring_export(k, v) + "\n"),
                    file_consumer=lambda f: fp.write(Environment.tostring_file(f) + "\n"),
                )
        if deactivate_file is not None:
            with deactivate_file.open("w") as fp:
                self.deactivate(
                    comment_consumer=lambda c: fp.write(Environment.tostring_comment(c) + "\n"),
                    kv_consumer=lambda k, v: fp.write(Environment.tostring_export(k, v) + "\n"),
                    file_consumer=lambda f: fp.write(Environment.tostring_file(f) + "\n"),
                )


class IEnvProvider(ABC):
    def __init__(self, label):
        self.__label = label

    @abstractmethod
    def _getenvmap(self) -> dict:
        pass

    def _getenvinfiles(self) -> list:
        return []

    def _getenvoutfiles(self) -> list:
        return []

    def build_environment(self, vr: callable = None) -> Environment:
        content = OrderedDict()
        for k, v in self._getenvmap().items():
            content[k] = vr(v) if vr else v
        in_files = []
        for f in self._getenvinfiles():
            in_files.append(vr(f) if vr else f)
        out_files = []
        for f in self._getenvoutfiles():
            out_files.append(vr(f) if vr else f)
        return Environment(label="Exported by {name}".format(name=self.__label), content=content, in_files=in_files, out_files=out_files)

    def update_environment(self, set_map: dict = None, unset_list: list = None):
        envmap = self._getenvmap()
        if set_map is not None:
            for k, v in set_map.items():
                envmap[k] = str(v)
        if unset_list is not None:
            for k in unset_list:
                if k in envmap:
                    del envmap[k]
