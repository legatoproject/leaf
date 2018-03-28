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
from pathlib import Path
import re
from tarfile import TarFile

from leaf.utils import resolveUrl, jsonLoad, jsonLoadFile, checkSupportedLeaf,\
    versionComparator_lt, stringToTuple


@total_ordering
class PackageIdentifier ():

    _NAME_REGEX = re.compile('^[a-zA-Z0-9][-a-zA-Z0-9]*$')
    _VERSION_REGEX = re.compile('^[a-zA-Z0-9][-._a-zA-Z0-9]*$')
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
        return versionComparator_lt(self.version,
                                    other.version)

    def getVersion(self):
        return stringToTuple(self.version)


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

    def isSupportedOs(self):
        supportedOs = self.getSupportedOS()
        return supportedOs is None or len(supportedOs) == 0 or LeafConstants.CURRENT_OS in supportedOs

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

    def getWsProfiles(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILES,
                             value=OrderedDict())


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
        out.getPackages()
        out.getEnv()
        return out

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        self.name = name
        self.folder = folder
        self.isCurrentProfile = False

    def getPackages(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_PACKAGES,
                             value=[])

    def getEnv(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_ENV,
                             value=OrderedDict())

    def addPackage(self, newpi):
        profilePiList = [PackageIdentifier.fromString(
            pis)for pis in self.getPackages()]
        profilePiList = [pi for pi in profilePiList if pi.name != newpi.name]
        profilePiList.append(newpi)
        self.json[JsonConstants.WS_PROFILE_PACKAGES] = [
            str(pi) for pi in profilePiList]

    def addPackages(self, piList):
        for pi in piList:
            self.addPackage(pi)
