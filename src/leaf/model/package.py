"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import io
import operator
import re
from builtins import ValueError, bool
from collections import OrderedDict
from functools import total_ordering
from pathlib import Path
from tarfile import TarFile

from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.error import InvalidPackageNameException
from leaf.core.jsonutils import JsonObject, jload, jloadfile
from leaf.core.utils import (url_resolve, version_comparator_lt,
                             version_string_to_tuple)
from leaf.model.environment import Environment, IEnvProvider
from leaf.model.settings import ScopeSetting

IDENTIFIER_GETTER = operator.attrgetter("identifier")


@total_ordering
class PackageIdentifier:

    NAME_PATTERN = "[a-zA-Z0-9][-a-zA-Z0-9]*"
    VERSION_PATTERN = "[a-zA-Z0-9][-._a-zA-Z0-9]*"
    SEPARATOR = "_"

    @staticmethod
    def is_valid_identifier(pis: str) -> bool:
        if isinstance(pis, str):
            split = pis.partition(PackageIdentifier.SEPARATOR)
            if len(split) == 3:
                if re.compile(PackageIdentifier.NAME_PATTERN).fullmatch(split[0]) is not None:
                    if re.compile(PackageIdentifier.VERSION_PATTERN).fullmatch(split[2]) is not None:
                        return True
        return False

    @staticmethod
    def parse(pis: str):
        if not PackageIdentifier.is_valid_identifier(pis):
            raise InvalidPackageNameException(pis)
        split = pis.partition(PackageIdentifier.SEPARATOR)
        return PackageIdentifier(split[0], split[2])

    @staticmethod
    def parse_list(pislist: list):
        return [PackageIdentifier.parse(pis) for pis in pislist]

    def __init__(self, name: str, version: str):
        if re.compile(PackageIdentifier.NAME_PATTERN).fullmatch(name) is None:
            raise ValueError("Invalid package name: " + name)
        if re.compile(PackageIdentifier.VERSION_PATTERN).fullmatch(version) is None:
            raise ValueError("Invalid package version: " + version)
        self.__name = name
        self.__version = version

    @property
    def name(self):
        return self.__name

    @property
    def version(self):
        return self.__version

    @property
    def version_tuple(self):
        return version_string_to_tuple(self.version)

    def __str__(self):
        return self.name + PackageIdentifier.SEPARATOR + self.version

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not isinstance(other, PackageIdentifier):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __lt__(self, other):
        if not isinstance(other, PackageIdentifier):
            return NotImplemented
        if not self.name == other.name:
            return self.name < other.name
        if self.version == other.version:
            return False
        return version_comparator_lt(self.version, other.version)


class ConditionalPackageIdentifier(PackageIdentifier):

    CONDITION_PATTERN = r"\((.+?)\)"
    COND_SET = "(!)?([A-Za-z0-9_]+)"
    COND_EQ = "([A-Za-z0-9_]+)(=|!=|~|!~)(.+)"

    @staticmethod
    def parse(pisc: str):
        p = re.compile(
            "({name}){separator}({version})({conditions})*".format(
                name=PackageIdentifier.NAME_PATTERN,
                separator=PackageIdentifier.SEPARATOR,
                version=PackageIdentifier.VERSION_PATTERN,
                conditions=ConditionalPackageIdentifier.CONDITION_PATTERN,
            )
        )
        m = p.fullmatch(pisc)
        if m is None:
            raise ValueError("Invalid conditional package identifier: {pi}".format(pi=pisc))
        conditions = re.compile(ConditionalPackageIdentifier.CONDITION_PATTERN).findall(pisc)
        return ConditionalPackageIdentifier(m.group(1), m.group(2), conditions)

    def __init__(self, name: str, version: str, conditions: list):
        PackageIdentifier.__init__(self, name, version)
        self.__conditions = conditions

    @property
    def conditions(self):
        return self.__conditions

    def are_conditions_satified(self, env: Environment) -> bool:
        if self.__conditions is None:
            return True
        for cond in self.__conditions:
            if not self.__is_condition_satified(cond, env):
                return False
        return True

    def __is_condition_satified(self, cond: str, env: Environment) -> bool:
        m = re.compile(ConditionalPackageIdentifier.COND_SET).fullmatch(cond)
        if m is not None:
            return (m.group(1) is None) ^ (env.find_value(m.group(2)) is None)

        m = re.compile(ConditionalPackageIdentifier.COND_EQ).fullmatch(cond)
        if m is not None:
            value = env.find_value(m.group(1))
            if m.group(2) == "!=":
                return value != m.group(3)
            elif m.group(2) == "=":
                return value == m.group(3)
            elif m.group(2) == "~":
                return value is not None and m.group(3).lower() in value.lower()
            elif m.group(2) == "!~":
                return value is None or m.group(3).lower() not in value.lower()

        raise ValueError("Unknown condition: {cond}".format(cond=cond))


class Manifest(JsonObject):

    """
    Represent a Manifest model object
    """

    @staticmethod
    def parse(mffile: Path):
        return Manifest(jloadfile(mffile))

    def __init__(self, json: dict):
        JsonObject.__init__(self, json)
        self.__custom_tags = []

    @property
    def identifier(self):
        return PackageIdentifier(self.name, self.version)

    @property
    def custom_tags(self):
        return self.__custom_tags

    @property
    def info_node(self):
        return self.jsonget(JsonConstants.INFO, mandatory=True)

    @property
    def name(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_NAME], mandatory=True)

    @property
    def date(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DATE])

    @property
    def version(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_VERSION], mandatory=True)

    @property
    def description(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DESCRIPTION])

    @property
    def master(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_MASTER], default=False)

    @property
    def final_size(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_FINALSIZE])

    @property
    def depends_packages(self) -> list:
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DEPENDS], default=[])

    @property
    def requires_packages(self) -> list:
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_REQUIRES], default=[])

    @property
    def leaf_min_version(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_LEAF_MINVER])

    @property
    def tags(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_TAGS], default=[])

    @property
    def all_tags(self):
        return self.custom_tags + self.tags

    @property
    def auto_upgrade(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_AUTOUPGRADE])

    def get_depends_from_env(self, env: Environment):
        out = []
        for pisc in self.depends_packages:
            cpi = ConditionalPackageIdentifier.parse(pisc)
            if cpi not in out and (env is None or cpi.are_conditions_satified(env)):
                out.append(cpi)
        return out

    def __str__(self):
        return str(self.identifier)


class LeafArtifact(Manifest):

    """
    Represent a tar/xz or a single manifest.json file
    """

    @staticmethod
    def __find_manifest(tarfile):
        for prefix in ("", "./"):
            out = prefix + LeafFiles.MANIFEST
            if out in tarfile.getnames():
                return out
        raise ValueError("Cannot find {file} in package".format(file=LeafFiles.MANIFEST))

    def __init__(self, path):
        self.__path = path
        with TarFile.open(str(self.__path), "r") as tarfile:
            mf = LeafArtifact.__find_manifest(tarfile)
            Manifest.__init__(self, jload(io.TextIOWrapper(tarfile.extractfile(mf))))

    @property
    def path(self):
        return self.__path

    def get_total_size(self):
        out = 0
        with TarFile.open(str(self.__path), "r") as tarfile:
            for ti in tarfile.getmembers():
                out += ti.size
        return out


class AvailablePackage(Manifest):

    """
    Represent a package available in a remote repository
    """

    def __init__(self, json: dict, url: str):
        Manifest.__init__(self, json)
        self.__url = url
        self.__remotes = []

    @property
    def size(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_SIZE)

    @property
    def filename(self):
        return Path(self.subpath).name

    @property
    def hashsum(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_HASH)

    @property
    def subpath(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_FILE, mandatory=True)

    @property
    def url(self):
        return url_resolve(self.__url, self.subpath)

    @property
    def remotes(self):
        return self.__remotes


class InstalledPackage(Manifest, IEnvProvider):

    """
    Represent an installed package
    """

    def __init__(self, mffile: Path, read_only=False):
        Manifest.__init__(self, jloadfile(mffile))
        IEnvProvider.__init__(self, "package {pi}".format(pi=self.identifier))
        self.__folder = mffile.parent
        self.__read_only = read_only
        if read_only:
            self.custom_tags.append("system")

    @property
    def folder(self):
        return self.__folder

    @property
    def read_only(self):
        return self.__read_only

    @property
    def binaries(self) -> dict:
        out = OrderedDict()
        for name, json in self.jsonget(JsonConstants.ENTRYPOINTS, default={}).items():
            out[name] = Entrypoint(name, json)
        return out

    @property
    def plugins(self) -> dict:
        out = OrderedDict()
        for name, json in self.jsonget(JsonConstants.PLUGINS, default={}).items():
            out[name] = PluginDefinition(name, self, json)
        return out

    @property
    def settings(self) -> dict:
        out = OrderedDict()
        for identifier, json in self.jsonget(JsonConstants.SETTINGS, default={}).items():
            sid = "{pkgname}.{id}".format(pkgname=self.name, id=identifier)
            out[sid] = ScopeSetting.from_json(sid, json)
        return out

    def _getenvmap(self) -> dict:
        return self.jsonget(JsonConstants.ENV, default={})

    def _getenvinfiles(self) -> list:
        return self.jsonget(JsonConstants.ENVIN, default=[])

    def _getenvoutfiles(self) -> list:
        return self.jsonget(JsonConstants.ENVOUT, default=[])


class PluginDefinition(JsonObject):
    def __init__(self, location: str, ip: InstalledPackage, json: dict):
        JsonObject.__init__(self, json)
        self.__location = location
        self.__ip = ip
        self.__command = None

    @property
    def name(self):
        return self.__location.split(" ")[-1]

    @property
    def location(self):
        return self.__location

    @property
    def prefix(self):
        return self.__location.split(" ")[0:-1]

    @property
    def installed_package(self):
        return self.__ip

    @property
    def command(self):
        return self.__command

    @command.setter
    def command(self, command):
        self.__command = command

    @property
    def description(self):
        return self.jsonget(JsonConstants.PLUGIN_DESCRIPTION)

    @property
    def source_file(self):
        out = self.installed_package.folder / self.jsonget(JsonConstants.PLUGIN_SOURCE, mandatory=True)
        if not out.exists():
            raise ValueError("Cannot find plugin source: {source}".format(source=out))
        return out

    @property
    def classname(self):
        return self.jsonget(JsonConstants.PLUGIN_CLASS)


class Entrypoint(JsonObject):
    def __init__(self, name, json):
        JsonObject.__init__(self, json)
        self.__name = name

    @property
    def name(self):
        return self.__name

    @property
    def command(self):
        return self.jsonget(JsonConstants.ENTRYPOINT_PATH, mandatory=True)

    @property
    def description(self):
        return self.jsonget(JsonConstants.ENTRYPOINT_DESCRIPTION)
