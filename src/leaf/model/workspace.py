'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from leaf.constants import JsonConstants, LeafFiles, LeafConstants

from leaf.model.base import JsonObject
from leaf.model.environment import IEnvObject
from leaf.model.package import InstalledPackage, PackageIdentifier


class Profile(JsonObject, IEnvObject):
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
        if name in ["", LeafFiles.CURRENT_PROFILE_LINKNAME]:
            raise ValueError("'%s' is not a valid profile name" % name)
        return name

    @staticmethod
    def emptyProfile(name, dataFolder):
        out = Profile(Profile.checkValidName(name),
                      dataFolder / name, OrderedDict())
        out.getPackages()
        out.getEnvMap()
        return out

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        IEnvObject.__init__(self, "profile %s " % name)
        self.name = name
        self.folder = folder
        self.isCurrentProfile = False

    def getEnvMap(self):
        if JsonConstants.WS_PROFILE_ENV not in self.json:
            self.json[JsonConstants.WS_PROFILE_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILE_ENV]

    def getEnvironment(self):
        out = super().getEnvironment()
        out.env.append(('LEAF_PROFILE', self.name))
        return out

    def getPackages(self):
        if JsonConstants.WS_PROFILE_PACKAGES not in self.json:
            self.json[JsonConstants.WS_PROFILE_PACKAGES] = []
        return self.json[JsonConstants.WS_PROFILE_PACKAGES]

    def addPackages(self, piList):
        pkgMap = self.getPackagesMap()
        for pi in piList:
            pkgMap[pi.name] = pi
        self.json[JsonConstants.WS_PROFILE_PACKAGES] = [
            str(pi) for pi in pkgMap.values()]

    def removePackages(self, piList):
        pkgList = [pi for pi in self.getPackagesMap().values()
                   if pi not in piList]
        self.json[JsonConstants.WS_PROFILE_PACKAGES] = [
            str(pi) for pi in pkgList]

    def getPackagesMap(self):
        out = OrderedDict()
        for pis in self.getPackages():
            pi = PackageIdentifier.fromString(pis)
            if pi.name not in out:
                out[pi.name] = pi
        return out

    def getLinkedPackages(self):
        '''
        Return a list of linked packages
        '''
        out = []
        for link in self.folder.iterdir():
            if link.is_symlink():
                try:
                    out.append(InstalledPackage(link / LeafFiles.MANIFEST))
                except Exception:
                    pass
        return out

    def __str__(self):
        return self.name
