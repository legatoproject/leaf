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
from leaf.constants import JsonConstants, LeafConstants, LeafFiles
from leaf.utils import resolveUrl, jsonLoad, jsonLoadFile, checkSupportedLeaf,\
    versionComparator_lt, stringToTuple
from pathlib import Path
import re
from tarfile import TarFile


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


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

    def jsoninit(self, *path, key=None, value=None, force=False):
        if key is None:
            raise ValueError("Cannot init json")
        parent = self.jsonpath(*path)
        if not isinstance(parent, dict):
            raise ValueError("Cannot init json")
        if force or key not in parent:
            parent[key] = value
        return parent[key]

    def jsonpath(self, *path, default=None):
        '''
        Utility to browse json and reduce None testing
        '''
        currentNode = self.json
        for p in path:
            if isinstance(currentNode, dict) and p in currentNode:
                currentNode = currentNode.get(p, default)
            else:
                return default
        return currentNode


class Manifest(JsonObject):
    '''
    Represent a Manifest model object
    '''

    @staticmethod
    def parse(manifestFile):
        return Manifest(jsonLoadFile(manifestFile))

    def __init__(self, json):
        JsonObject.__init__(self, json)
        self.tags = []

    def __str__(self):
        return str(self.getIdentifier())

    def getNodeInfo(self):
        return self.jsonpath(JsonConstants.INFO)

    def getName(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_NAME)

    def getVersion(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_VERSION)

    def getIdentifier(self):
        return PackageIdentifier(self.getName(), self.getVersion())

    def getDescription(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_DESCRIPTION)

    def isMaster(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_MASTER, default=False)

    def getLeafDepends(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_DEPENDS, JsonConstants.INFO_DEPENDS_LEAF, default=[])

    def getLeafDepends2(self, env):
        out = []
        for pisc in self.getLeafDepends():
            cpi = ConditionalPackageIdentifier.fromString(pisc)
            if cpi not in out and (env is None or cpi.isOk(env)):
                out.append(cpi)
        return out

    def getAptDepends(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_DEPENDS, JsonConstants.INFO_DEPENDS_DEB, default=[])

    def getSupportedModules(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_SUPPORTEDMODULES)

    def getSupportedLeafVersion(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_LEAF_MINVER)

    def isSupportedByCurrentLeafVersion(self):
        return checkSupportedLeaf(self.getSupportedLeafVersion())


class LeafArtifact(Manifest):
    '''
    Represent a tar/xz or a single manifest.json file
    '''

    def __init__(self, path):
        self.path = path
        with TarFile.open(str(self.path), 'r') as tarfile:
            Manifest.__init__(self,
                              jsonLoad(io.TextIOWrapper(tarfile.extractfile(LeafConstants.MANIFEST))))


class AvailablePackage(Manifest):
    '''
    Represent a package available in a remote repository
    '''

    def __init__(self, jsonPayload, remoteUrl):
        super().__init__(jsonPayload)
        self.remoteUrl = remoteUrl

    def __str__(self, *args, **kwargs):
        return "{pi} [{path}] ({size} bytes)".format(
            pi=str(self.getIdentifier()),
            path=self.getSubPath(),
            size=self.getSize())

    def getSize(self):
        return self.jsonpath(JsonConstants.REMOTE_PACKAGE_SIZE)

    def getFilename(self):
        return Path(self.getSubPath()).name

    def getSha1sum(self):
        return self.jsonpath(JsonConstants.REMOTE_PACKAGE_SHA1SUM)

    def getSubPath(self):
        return self.jsonpath(JsonConstants.REMOTE_PACKAGE_FILE)

    def getUrl(self):
        return resolveUrl(self.remoteUrl, self.getSubPath())


class InstalledPackage(Manifest):
    '''
    Represent an installed package
    '''

    def __init__(self, manifestFile):
        super().__init__(jsonLoadFile(manifestFile))
        self.folder = manifestFile.parent

    def __str__(self):
        return "{pi} [{path}]".format(pi=self.getIdentifier(), path=str(self.folder))

    def getMfEnv(self):
        return self.jsonpath(JsonConstants.ENV, default={})


class RemoteRepository(JsonObject):
    '''
    Represent a remote repository
    '''

    def __init__(self, url, isRootRepository, json=None):
        JsonObject.__init__(self, json)
        self.isRootRepository = isRootRepository
        self.url = url

    def isFetched(self):
        return self.json is not None

    def getPackages(self):
        return self.jsonpath(JsonConstants.REMOTE_PACKAGES, default=[])


class WorkspaceConfiguration(JsonObject):
    '''
    Represent a workspace configuration, ie Profiles, env ...
    '''

    def __init__(self, json):
        JsonObject.__init__(self, json)

    def getWsEnv(self):
        return self.jsoninit(key=JsonConstants.WS_ENV,
                             value=OrderedDict())

    def getWsEnvironment(self):
        return Environment("Exported by workspace config",
                           self.getWsEnv())

    def getWsRemotes(self):
        return self.jsoninit(key=JsonConstants.WS_REMOTES,
                             value=[])

    def getWsProfiles(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILES,
                             value=OrderedDict())

    def getWsSupportedModules(self):
        return self.jsoninit(key=JsonConstants.WS_MODULES,
                             value=[])


class Profile(JsonObject):
    '''
    Represent a profile inside a workspace
    '''

    @staticmethod
    def genDefaultName(piList):
        if piList is not None and len(piList) > 0:
            return Profile.checkValidName("_".join([pi.name.upper() for pi in piList]))
        return LeafConstants.DEFAULT_PROFILE

    @staticmethod
    def checkValidName(name):
        if not isinstance(name, str):
            raise ValueError("Profile name must be a string")
        if name in ["", LeafFiles.CURRENT_PROFILE]:
            raise ValueError("'%s' is not a valid profile name" % name)
        return name

    @staticmethod
    def emptyProfile(name, folder):
        out = Profile(Profile.checkValidName(name), folder, OrderedDict())
        out.getPfPackages()
        out.getPfEnv()
        return out

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        self.name = name
        self.folder = folder
        self.isCurrentProfile = False

    def getPfEnv(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_ENV,
                             value=OrderedDict())

    def getPfEnvironment(self):
        return Environment("Exported by profile %s" % self.name,
                           self.getPfEnv())

    def getPfPackages(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_PACKAGES,
                             value=[])

    def getPfPackageIdentifiers(self):
        return list(map(PackageIdentifier.fromString,
                        self.jsoninit(key=JsonConstants.WS_PROFILE_PACKAGES,
                                      value=[])))

    def getPfPackageIdentifierMap(self):
        out = OrderedDict()
        for pis in self.getPfPackages():
            pi = PackageIdentifier.fromString(pis)
            if pi.name not in out:
                out[pi.name] = pi
        return out

    def setPiList(self, piList):
        self.json[JsonConstants.WS_PROFILE_PACKAGES] = [str(pi)
                                                        for pi in piList]


class Environment():

    @staticmethod
    def exportCommand(key, value):
        return "export %s=\"%s\";" % (key, value)

    @staticmethod
    def unsetCommand(key):
        return "unset %s" % (key)

    def __init__(self, comment=None, content=None):
        self.comment = comment
        self.env = []
        self.children = []
        if isinstance(content, dict):
            self.env += content.items()
        elif isinstance(content, list):
            self.env += content

    def addSubEnv(self, child):
        if child is not None:
            if not isinstance(child, Environment):
                raise ValueError()
            self.children.append(child)

    def printEnv(self, commentConsumer=None, kvConsumer=None):
        if len(self.env) > 0:
            if self.comment is not None and commentConsumer is not None:
                commentConsumer(self.comment)
            if kvConsumer is not None:
                for k, v in self.env:
                    kvConsumer(k, v)
        for e in self.children:
            e.printEnv(commentConsumer, kvConsumer)

    def toList(self, acc=None):
        if acc is None:
            acc = []
        acc += self.env
        for e in self.children:
            e.toList(acc=acc)
        return acc

    def keys(self):
        out = set()
        for k, _ in self.toList():
            out.add(k)
        return out

    def findValue(self, key):
        out = None
        for k, v in self.env:
            if k == key:
                out = v
        for c in self.children:
            out2 = c.findValue(key)
            if out2 is not None:
                out = out2
        return out

    def unset(self, key):
        if key in self.env:
            del self.env[key]
        for c in self.children:
            c.unset(key)
