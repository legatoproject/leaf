'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from functools import total_ordering
import io
from leaf.constants import JsonConstants, LeafFiles
from pathlib import Path
import re
from tarfile import TarFile

from leaf.model.base import JsonObject
from leaf.utils import resolveUrl, jsonLoad, jsonLoadFile, checkSupportedLeaf, \
    versionComparator_lt, stringToTuple


@total_ordering
class PackageIdentifier ():

    NAME_PATTERN = '[a-zA-Z0-9][-a-zA-Z0-9]*'
    VERSION_PATTERN = '[a-zA-Z0-9][-._a-zA-Z0-9]*'
    SEPARATOR = '_'

    @staticmethod
    def isValidIdentifier(pis):
        split = pis.partition(PackageIdentifier.SEPARATOR)
        return (re.compile(PackageIdentifier.NAME_PATTERN).fullmatch(split[0]) is not None and
                re.compile(PackageIdentifier.VERSION_PATTERN).fullmatch(split[2]) is not None)

    @staticmethod
    def fromString(pis):
        split = pis.partition(PackageIdentifier.SEPARATOR)
        return PackageIdentifier(split[0], split[2])

    @staticmethod
    def fromStringList(pisList):
        return [PackageIdentifier.fromString(pis) for pis in pisList]

    def __init__(self, name, version):
        if re.compile(PackageIdentifier.NAME_PATTERN).fullmatch(name) is None:
            raise ValueError("Invalid package name: " + name)
        if re.compile(PackageIdentifier.VERSION_PATTERN).fullmatch(version) is None:
            raise ValueError("Invalid package version: " + version)
        self.name = name
        self.version = version

    def __str__(self):
        return self.name + PackageIdentifier.SEPARATOR + self.version

    def _is_valid_operand(self, other):
        return (hasattr(other, "name") and
                hasattr(other, "version"))

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        if not self.name == other.name:
            return self.name < other.name
        if self.version == other.version:
            return False
        return versionComparator_lt(self.version,
                                    other.version)

    def getVersion(self):
        return stringToTuple(self.version)


class ConditionalPackageIdentifier(PackageIdentifier):

    CONDITION_PATTERN = '\((.+?)\)'
    COND_SET = "(!)?([A-Za-z0-9_]+)"
    COND_EQ = "([A-Za-z0-9_]+)(=|!=|~|!~)(.+)"

    @staticmethod
    def fromString(pisc):
        p = re.compile("(%s)%s(%s)(%s)*" % (PackageIdentifier.NAME_PATTERN,
                                            PackageIdentifier.SEPARATOR,
                                            PackageIdentifier.VERSION_PATTERN,
                                            ConditionalPackageIdentifier.CONDITION_PATTERN))
        m = p.fullmatch(pisc)
        if m is None:
            raise ValueError("Invalid conditional package identifier: %s" %
                             pisc)
        conditions = re.compile(
            ConditionalPackageIdentifier.CONDITION_PATTERN).findall(pisc)
        return ConditionalPackageIdentifier(m.group(1), m.group(2), conditions)

    def __init__(self, name, version, conditions):
        PackageIdentifier.__init__(self, name, version)
        self.conditions = conditions

    def isOk(self, env):
        if self.conditions is None:
            return True
        for cond in self.conditions:
            if not ConditionalPackageIdentifier.isValidCondition(cond, env):
                return False
        return True

    @staticmethod
    def isValidCondition(cond, env):
        m = re.compile(ConditionalPackageIdentifier.COND_SET).fullmatch(cond)
        if m is not None:
            return (m.group(1) is None) ^ (env.findValue(m.group(2)) is None)

        m = re.compile(ConditionalPackageIdentifier.COND_EQ).fullmatch(cond)
        if m is not None:
            value = env.findValue(m.group(1))
            if m.group(2) == "!=":
                return value != m.group(3)
            elif m.group(2) == "=":
                return value == m.group(3)
            elif m.group(2) == "~":
                return value is not None and m.group(3).lower() in value.lower()
            elif m.group(2) == "!~":
                return value is None or m.group(3).lower() not in value.lower()

        raise ValueError("Unknown condition: %s" % cond)


class Manifest(JsonObject):
    '''
    Represent a Manifest model object
    '''

    @staticmethod
    def parse(manifestFile):
        return Manifest(jsonLoadFile(manifestFile))

    def __init__(self, json):
        JsonObject.__init__(self, json)
        self.customTags = []

    def __str__(self):
        return str(self.getIdentifier())

    def getNodeInfo(self):
        return self.jsonget(JsonConstants.INFO, mandatory=True)

    def getName(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_NAME], mandatory=True)

    def getDate(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DATE])

    def getVersion(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_VERSION], mandatory=True)

    def getIdentifier(self):
        return PackageIdentifier(self.getName(), self.getVersion())

    def getDescription(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DESCRIPTION])

    def isMaster(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_MASTER], default=False)

    def getLeafDepends(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_DEPENDS], default=[])

    def getLeafRequires(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_REQUIRES], default=[])

    def getLeafDependsFromEnv(self, env):
        out = []
        for pisc in self.getLeafDepends():
            cpi = ConditionalPackageIdentifier.fromString(pisc)
            if cpi not in out and (env is None or cpi.isOk(env)):
                out.append(cpi)
        return out

    def getSupportedLeafVersion(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_LEAF_MINVER])

    def isSupportedByCurrentLeafVersion(self):
        return checkSupportedLeaf(self.getSupportedLeafVersion())

    def getTags(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_TAGS], default=[])

    def getAllTags(self):
        return self.customTags + self.getTags()

    def getFeatures(self):
        return self.jsonpath([JsonConstants.INFO, JsonConstants.INFO_FEATURES], default={})

    def getFeaturesMap(self):
        out = OrderedDict()
        for name, json in self.getFeatures().items():
            out[name] = Feature(name, json)
        return out


class LeafArtifact(Manifest):
    '''
    Represent a tar/xz or a single manifest.json file
    '''

    def __init__(self, path):
        self.path = path
        with TarFile.open(str(self.path), 'r') as tarfile:
            Manifest.__init__(self, jsonLoad(io.TextIOWrapper(
                tarfile.extractfile(LeafFiles.MANIFEST))))


class AvailablePackage(Manifest):
    '''
    Represent a package available in a remote repository
    '''

    def __init__(self, jsonPayload, remoteUrl):
        Manifest.__init__(self, jsonPayload)
        self.remoteUrl = remoteUrl
        self.sourceRemotes = []

    def getSize(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_SIZE)

    def getFilename(self):
        return Path(self.getSubPath()).name

    def getSha1sum(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_SHA1SUM)

    def getSubPath(self):
        return self.jsonget(JsonConstants.REMOTE_PACKAGE_FILE, mandatory=True)

    def getUrl(self):
        return resolveUrl(self.remoteUrl, self.getSubPath())


class InstalledPackage(Manifest):
    '''
    Represent an installed package
    '''

    def __init__(self, manifestFile):
        Manifest.__init__(self, jsonLoadFile(manifestFile))
        self.folder = manifestFile.parent

    def getEnvMap(self):
        return self.jsonget(JsonConstants.ENV, OrderedDict())


class Feature(JsonObject):
    '''
    Reprensent a leaf feature, ie constants for a given env var
    '''

    def __init__(self, name, json):
        JsonObject.__init__(self, json)
        self.name = name
        self.aliases = []

    def addAlias(self, other):
        if not isinstance(other, Feature):
            raise ValueError()
        if self.name != other.name:
            raise ValueError("Cannot alias feature with different name")
        if self != other and other not in self.aliases:
            self.aliases.append(other)

    def getValue(self, enum):
        self.check()
        values = []

        def visit(f):
            if enum in f.getValues():
                value = f.getValues().get(enum)
                if value not in values:
                    values.append(value)
            for alias in f.aliases:
                visit(alias)

        visit(self)
        if len(values) == 0:
            raise ValueError("Cannot find %s in feature %s" %
                             (enum, self.name))
        if len(values) > 1:
            raise ValueError("Multiple definition for %s in feature %s" %
                             (enum, self.name))
        return values[0]

    def retrieveEnumsForValue(self, value):
        self.check()
        out = []

        def visit(f):
            for k, v in f.getValues().items():
                if v == value and k not in out:
                    out.append(k)
            for alias in f.aliases:
                visit(alias)
        visit(self)
        return out

    def check(self):
        expectedKey = self.getKey()

        def visit(f):
            if f.getKey() != expectedKey:
                raise ValueError("Invalid feature %s" % (self.name))
            for alias in f.aliases:
                visit(alias)
        visit(self)

    def getDescription(self):
        # Can be None
        return self.json.get(JsonConstants.INFO_FEATURE_DESCRIPTION)

    def getKey(self):
        return self.json[JsonConstants.INFO_FEATURE_KEY]

    def getValues(self):
        return self.json.get(JsonConstants.INFO_FEATURE_VALUES, {})

    def __eq__(self, other):
        return isinstance(other, Feature) and \
            self.name == other.name and \
            self.getKey() == other.getKey() and \
            self.getValues() == other.getValues() and \
            self.getDescription() == other.getDescription()
