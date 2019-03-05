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
from leaf.core.error import InvalidPackageNameException, LeafException
from leaf.core.jsonutils import JsonObject, jload, jloadfile
from leaf.core.utils import url_resolve, version_comparator_lt, version_string_to_tuple
from leaf.model.environment import Environment

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

    @property
    def features(self) -> list:
        out = []
        for name, json in self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_FEATURES], default={}).items():
            out.append(Feature(name, json))
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


class InstalledPackage(Manifest):

    """
    Represent an installed package
    """

    def __init__(self, mffile: Path):
        Manifest.__init__(self, jloadfile(mffile))
        self.__folder = mffile.parent

    @property
    def folder(self):
        return self.__folder

    @property
    def envmap(self):
        return self.jsonget(JsonConstants.ENV, default={})

    @property
    def binaries(self) -> list:
        out = OrderedDict()
        for name, json in self.jsonget(JsonConstants.ENTRYPOINTS, default={}).items():
            out[name] = Entrypoint(name, json)
        return out

    @property
    def plugins(self) -> list:
        out = OrderedDict()
        for name, json in self.jsonget(JsonConstants.PLUGINS, default={}).items():
            out[name] = PluginDefinition(name, self, json)
        return out


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


class Feature(JsonObject):

    """
    Reprensent a leaf feature, ie constants for a given env var
    """

    def __init__(self, name, json):
        JsonObject.__init__(self, json)
        self.__name = name
        self.__aliases = []

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return "{name}={values}".format(name=self.name, values="|".join(sorted(self.values.keys())))

    def add_alias(self, other):
        if not isinstance(other, Feature):
            raise ValueError()
        if self.name != other.name:
            raise LeafException("Cannot alias feature with different name")
        if self != other and other not in self.__aliases:
            self.__aliases.append(other)

    def get_value(self, enum):
        self.check()
        out = []

        def visit(f):
            if enum in f.values:
                value = f.values.get(enum)
                if value not in out:
                    out.append(value)
            for alias in f.__aliases:
                visit(alias)

        visit(self)
        if len(out) == 0:
            raise LeafException("Cannot find {enum} in feature {name}".format(enum=enum, name=self.name))
        if len(out) > 1:
            raise LeafException("Multiple definition for {enum} in feature {name}".format(enum=enum, name=self.name))
        return out[0]

    def retrieve_enums_for_value(self, value):
        self.check()
        out = []

        def visit(f):
            for k, v in f.values.items():
                if v == value and k not in out:
                    out.append(k)
            for alias in f.__aliases:
                visit(alias)

        visit(self)
        return out

    def check(self):
        def visit(f, expected_key):
            if f.key != expected_key:
                raise LeafException("Invalid feature {name}".format(name=self.name))
            for alias in f.__aliases:
                visit(alias, expected_key)

        visit(self, self.key)

    @property
    def description(self):
        # Can be None
        return self.json.get(JsonConstants.INFO_FEATURE_DESCRIPTION)

    @property
    def key(self):
        return self.json[JsonConstants.INFO_FEATURE_KEY]

    @property
    def values(self):
        return self.json.get(JsonConstants.INFO_FEATURE_VALUES, {})

    def __eq__(self, other):
        return (
            isinstance(other, Feature)
            and self.name == other.name
            and self.key == other.key
            and self.description == other.description
            and self.values == other.values
        )


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

    @property
    def shell(self):
        return self.jsonget(JsonConstants.ENTRYPOINT_SHELL, default=True)
