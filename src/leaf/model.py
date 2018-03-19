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
from leaf.constants import JsonConstants, LeafConstants
from leaf.utils import resolveUrl, jsonLoad, jsonLoadFile
from pathlib import Path
import re
from tarfile import TarFile


@total_ordering
class PackageIdentifier ():

    _NAME_REGEX = re.compile('^[a-zA-Z0-9][-a-zA-Z0-9]*$')
    _VERSION_REGEX = re.compile('^[a-zA-Z0-9][-._a-zA-Z0-9]*$')
    _VERSION_SEPARATOR = re.compile("[-_.~]")
    _SEPARATOR = '_'

    @staticmethod
    def isValidIdentifier(pis):
        split = pis.partition(PackageIdentifier._SEPARATOR)
        return (PackageIdentifier._NAME_REGEX.match(split[0]) is not None and
                PackageIdentifier._VERSION_REGEX.match(split[2]) is not None)

    @staticmethod
    def fromString(pis):
        split = pis.partition(PackageIdentifier._SEPARATOR)
        return PackageIdentifier(split[0], split[2])

    @staticmethod
    def fromStringList(pisList):
        return [PackageIdentifier.fromString(pis) for pis in pisList]

    def __init__(self, name, version):
        if PackageIdentifier._NAME_REGEX.match(name) is None:
            raise ValueError("Invalid package name: " + name)
        if PackageIdentifier._VERSION_REGEX.match(version) is None:
            raise ValueError("Invalid package version: " + version)
        self.name = name
        self.version = version

    def __str__(self):
        return self.name + PackageIdentifier._SEPARATOR + self.version

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
        versionA = self.getVersion()
        versionB = other.getVersion()
        i = 0
        while True:
            if i >= len(versionA):
                return True
            if i >= len(versionB):
                return False
            a = versionA[i]
            b = versionB[i]
            if not type(a) == type(b):
                a = str(a)
                b = str(b)
            if not a == b:
                return a < b
            i += 1

    def getVersion(self):
        def tryint(x):
            try:
                return int(x)
            except:
                return x
        return tuple(tryint(x) for x in PackageIdentifier._VERSION_SEPARATOR.split(self.version))


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

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

    def getAptDepends(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_DEPENDS, JsonConstants.INFO_DEPENDS_DEB, default=[])

    def getSupportedModules(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_SUPPORTEDMODULES)

    def getSupportedOS(self):
        return self.jsonpath(JsonConstants.INFO, JsonConstants.INFO_SUPPORTEDOS)

    def isSupported(self):
        supportedOs = self.getSupportedOS()
        return supportedOs is None or len(supportedOs) == 0 or LeafConstants.CURRENT_OS in supportedOs


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


class RemoteRepository(JsonObject):
    '''
    Represent a remote repository
    '''

    def __init__(self, url, json=None):
        JsonObject.__init__(self, json)
        self.url = url

    def isFetched(self):
        return self.json is not None


class Profile(JsonObject):
    '''
    Represent a profile inside a workspace
    '''
    @staticmethod
    def emptyProfile(name, folder):
        json = OrderedDict()
        json[JsonConstants.PROFILE_PACKAGES] = []
        json[JsonConstants.PROFILE_ENV] = OrderedDict()
        return Profile(name, folder, json)

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        self.name = name
        self.folder = folder
        self.isCurrentProfile = False

    def getPackages(self):
        return self.jsonpath(JsonConstants.PROFILE_PACKAGES, default=[])

    def getEnv(self):
        return self.jsonpath(JsonConstants.PROFILE_ENV, default={})

    def addPackages(self, piList, clear=False):
        if clear or JsonConstants.PROFILE_PACKAGES not in self.json:
            self.json[JsonConstants.PROFILE_PACKAGES] = []
        if piList is not None:
            for pis in map(str, piList):
                if pis not in self.json[JsonConstants.PROFILE_PACKAGES]:
                    self.json[JsonConstants.PROFILE_PACKAGES].append(pis)

    def addEnv(self, envMap, clear=False):
        if clear or JsonConstants.PROFILE_ENV not in self.json:
            self.json[JsonConstants.PROFILE_ENV] = OrderedDict()
        if envMap is not None:
            self.json[JsonConstants.PROFILE_ENV].update(envMap)
